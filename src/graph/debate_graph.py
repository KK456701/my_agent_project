"""
LangGraph 辩论图 — 多智能体代码审查的核心编排

图结构：

    START
      ↓
  [route_pr]   ← 分级路由：快速通道 / 双Agent / 全阵容
      ↓
  [parallel_review]  ← 并行审查 (Send API)
      ↓
  [merge_findings]   ← 汇聚所有 Agent 的发现
      ↓
  [detect_conflicts] ← 碰撞检测
      ↓
    ┌── 有冲突? ── 否 ──→ [generate_report] → END
    ↓  是
  [debate_round]   ← 辩论循环（最多 MAX_DEBATE_ROUNDS 轮）
      ↓
  [check_consensus] ← 裁决
      ↓
    ┌── 已共识? ── 是 ──→ [generate_report] → END
    ↓  否
    ┌── 轮次 < MAX? ── 是 ──→ [debate_round] (循环)
    ↓  否
  [escalate_to_human] → [generate_report] → END
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from src.graph.state import DebateState
from src.agents.security_agent import SecurityReviewAgent
from src.agents.performance_agent import PerformanceReviewAgent
from src.agents.architecture_agent import ArchitectureReviewAgent
from src.agents.consensus_agent import ConsensusAgent
from src.tools.code_analyzer import count_diff_lines, count_diff_files, detect_conflicts, truncate_diff
from src.tools.smart_router import smart_route, RouteMode
from config import config


# ============================================================
# 节点函数
# ============================================================

def route_pr(state: DebateState) -> dict:
    """
    节点 1：智能分级路由

    三维度综合决策（非简单行数对比）：
    1. 关键文件识别 — auth.py/payment.py → 强制 full
    2. 文件类型感知 — 纯配置变更 → 降级 fast；核心代码 → 升级
    3. Commit 语义分析 — hotfix → 降级；refactor → 强制 full
    
    兜底：文件数 > 5 或行数 ≥ 200 → full
    """
    diff = state["pr_diff"]
    files = state["pr_files"]
    commit_msg = state.get("commit_message", "")

    changed_lines = count_diff_lines(diff)
    changed_files = count_diff_files(diff)

    mode, reason = smart_route(
        changed_lines=changed_lines,
        changed_files=changed_files,
        files=files,
        commit_message=commit_msg,
        fast_track_max_lines=config.FAST_TRACK_MAX_LINES,
    )

    domain_map = {
        RouteMode.FAST: ["security"],
        RouteMode.DUAL: ["security", "performance"],
        RouteMode.FULL: ["security", "performance", "architecture"],
    }

    return {
        "review_mode": mode.value,
        "route_reason": reason,
        "active_domains": domain_map[mode],
        "debate_round": 0,
        "conflicts": [],
        "escalated": False,
        "total_tokens": 0,
        "error": "",
    }


def continue_to_reviews(state: DebateState) -> list[Send]:
    """
    并行调度：根据 active_domains 向不同 Agent 发送审查任务
    
    使用 LangGraph Send API 实现真正的并行执行
    
    ⚠️ 注意：Send 不会自动继承父节点 state，
    必须显式传递 review_node 需要的所有字段
    """
    domains = state["active_domains"]
    sends = []
    for domain in domains:
        sends.append(Send("review_node", {
            "domain": domain,
            "pr_diff": state["pr_diff"],
            "pr_files": state["pr_files"],
        }))
    return sends


async def review_node(state: DebateState) -> dict:
    """
    节点 2（可并行执行）：单个 Agent 执行审查
    
    ⚡ 优化：
    - diff 截断（大文件）
    - Linter 静态分析注入（秒出结果，LLM 跳过）
    - Skills 知识库注入（按文件类型）
    """
    domain = state.get("domain", "security")
    diff = state["pr_diff"]
    files = state["pr_files"]

    # 截断过大的 diff
    from src.tools.code_analyzer import truncate_diff
    diff = truncate_diff(diff, max_lines=600)

    # ── Linter 静态分析（运行一次，所有 Agent 共享）──
    linter_prompt = ""
    if domain == "security":  # 只在第一个 Agent 运行时执行 linter
        try:
            from src.tools.linter_runner import run_python_linter, linter_results_to_prompt
            # 从 diff 中还原真实代码（去掉 +/- 前缀）
            code_lines = []
            for line in diff.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    code_lines.append(line[1:])
                elif not line.startswith("-") and not line.startswith("---") and not line.startswith("diff ") and not line.startswith("@@"):
                    code_lines.append(line)
            code = "\n".join(code_lines)

            linter_results = run_python_linter(code)
            linter_prompt = linter_results_to_prompt(linter_results)
        except Exception:
            pass  # Linter 失败不影响主流程

    # ── Skills 知识库 ──
    skill_prompt = ""
    try:
        from src.tools.skills_loader import get_skill_prompt_injection
        skill_injections = get_skill_prompt_injection(files)
        skill_prompt = skill_injections.get(domain, "")
    except Exception:
        pass

    # 选择对应 Agent
    agents = {
        "security": SecurityReviewAgent,
        "performance": PerformanceReviewAgent,
        "architecture": ArchitectureReviewAgent,
    }

    agent_cls = agents.get(domain)
    if not agent_cls:
        return {}

    agent = agent_cls()

    # 注入 Linter + Skills 到 Agent（在调用前修改 system prompt）
    if linter_prompt or skill_prompt:
        extra = (linter_prompt or "") + (skill_prompt or "")
        agent.system_prompt = agent.system_prompt + extra

    findings = await agent.review(diff, files)

    # 每个领域的结果写入对应字段
    result_key = f"{domain}_findings"
    return {result_key: findings}


def merge_findings(state: DebateState) -> dict:
    """
    节点 3：汇聚所有 Agent 的发现
    
    各 Agent 的 findings 已通过 operator.add reducer 自动合并到对应列表
    这里做冲突检测
    """
    findings_by_domain = {
        "security": state.get("security_findings", []),
        "performance": state.get("performance_findings", []),
        "architecture": state.get("architecture_findings", []),
    }

    return {"_findings_by_domain": findings_by_domain}


def detect_conflicts_node(state: DebateState) -> dict:
    """
    节点 4：冲突检测
    
    找出不同 Agent 对同一代码区域产生的不同判断
    """
    findings_by_domain = {
        "security": state.get("security_findings", []),
        "performance": state.get("performance_findings", []),
        "architecture": state.get("architecture_findings", []),
    }

    conflicts = detect_conflicts(findings_by_domain)

    return {"conflicts": conflicts}


def decide_after_detect(state: DebateState) -> Literal["debate_round", "generate_report"]:
    """条件边：有冲突就进入辩论，否则直接生成报告"""
    if state.get("conflicts") and len(state["conflicts"]) > 0:
        return "debate_round"
    return "generate_report"


async def debate_round(state: DebateState) -> dict:
    """
    节点 5：辩论轮次 — 并行裁决所有冲突
    
    ⚡ 优化：所有冲突并发裁决（asyncio.gather），而非串行 for 循环
    之前：35 个冲突 × 3s = 105s
    现在：35 个冲突并发 → ~5s（等最慢的那个）
    """
    import asyncio

    conflicts = state.get("conflicts", [])
    debate_round = state.get("debate_round", 0)
    debate_history = state.get("debate_history", [])

    if not conflicts:
        return {"debate_round": debate_round + 1}

    # ── 并行裁决所有冲突（信号量控制并发）──
    MAX_CONCURRENT = 8  # 最多同时 8 个裁决请求，避免 API 限流
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def resolve_one(conflict: dict):
        """裁决单个冲突（在 gather 中并发执行）"""
        if conflict.get("status") == "resolved":
            return ("skip", conflict)

        async with semaphore:
            consensus_agent = ConsensusAgent()
            resolution = await consensus_agent.resolve(conflict, debate_history)

        conflict["debate_rounds"] = debate_round + 1

        if resolution.get("resolution") == "stalemate":
            if debate_round + 1 >= config.MAX_DEBATE_ROUNDS:
                conflict["status"] = "escalated"
                return ("escalated", conflict)
            else:
                return ("pending", conflict)
        else:
            conflict["status"] = "resolved"
            conflict["resolution"] = resolution.get("final_suggestion", "")
            conflict["reasoning"] = resolution.get("reasoning", "")
            return ("resolved", conflict)

    # 所有冲突并行裁决！
    results = await asyncio.gather(*[resolve_one(c) for c in conflicts])

    resolved = []
    still_pending = []
    for status, conflict in results:
        if status == "resolved":
            resolved.append(conflict)
        elif status in ("escalated", "pending"):
            still_pending.append(conflict)
        # "skip" = 已经 resolved 的，放回 resolved
        else:
            resolved.append(conflict)

    # 记录本轮辩论历史
    new_history = [
        {
            "round": debate_round + 1,
            "conflict_id": c.get("conflict_id"),
            "status": c.get("status"),
            "resolution": c.get("resolution", ""),
        }
        for c in conflicts
    ]

    return {
        "conflicts": resolved + still_pending,
        "debate_round": debate_round + 1,
        "debate_history": new_history,
    }


def decide_after_debate(state: DebateState) -> Literal["debate_round", "escalate", "generate_report"]:
    """条件边：辩论后的路由决策"""
    conflicts = state.get("conflicts", [])
    debate_round = state.get("debate_round", 0)

    # 所有冲突都已解决
    pending = [c for c in conflicts if c.get("status") not in ("resolved", "escalated")]
    if not pending:
        return "generate_report"

    # 还有未解决的，但轮次已到上限 → 升级
    if debate_round >= config.MAX_DEBATE_ROUNDS:
        return "escalate"

    # 继续辩论
    return "debate_round"


def escalate_to_human(state: DebateState) -> dict:
    """
    节点 6：升级给人工审查者
    
    标记所有未解决的冲突为 escalated
    """
    conflicts = state.get("conflicts", [])
    for c in conflicts:
        if c.get("status") not in ("resolved", "escalated"):
            c["status"] = "escalated"

    return {"conflicts": conflicts, "escalated": True}


def generate_report(state: DebateState) -> dict:
    """
    节点 7：生成双格式审查报告
    
    1. Markdown 报告 — 给人看（完整辩论过程）
    2. Fixer Payload — 给下游 Agent 消费（结构化，只含可执行修复指令）
    """
    import json as json_mod

    security = state.get("security_findings", [])
    performance = state.get("performance_findings", [])
    architecture = state.get("architecture_findings", [])
    conflicts = state.get("conflicts", [])
    debate_round = state.get("debate_round", 0)
    mode = state.get("review_mode", "fast")

    report_parts = [
        f"# 🔍 多智能体代码审查报告\n",
        f"**审查模式**: {mode}",
        f"**辩论轮次**: {debate_round}",
        f"**PR 标题**: {state.get('pr_title', 'N/A')}\n",
        "---\n",
    ]

    # ── Linter 静态分析（非 LLM，秒出结果）──
    try:
        from src.tools.linter_runner import run_python_linter, linter_results_to_prompt
        diff = state.get("pr_diff", "")
        code_lines = []
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                code_lines.append(line[1:])
            elif not line.startswith("-") and not line.startswith("---") and not line.startswith("diff ") and not line.startswith("@@"):
                code_lines.append(line)
        code = "\n".join(code_lines)
        lr = run_python_linter(code)
        lp = linter_results_to_prompt(lr)
        if lp:
            report_parts.append(lp)
    except Exception:
        pass

    # ── Skills 知识库摘要 ──
    try:
        from src.tools.skills_loader import load_skills_for_files
        skills = load_skills_for_files(state.get("pr_files", []))
        if skills:
            report_parts.append("\n\n---\n## 📘 已加载的团队编码规范 (Skills)\n")
            for domain, content in skills.items():
                dc = {"security": "🛡️ 安全", "performance": "⚡ 性能", "architecture": "🏗️ 架构"}.get(domain, domain)
                report_parts.append(f"- {dc}: {len(content)} 字符的团队最佳实践已注入审查\n")
    except Exception:
        pass

    # 各 Agent 发现
    all_domain_findings = {
        "🛡️ 安全检查": security,
        "⚡ 性能分析": performance,
        "🏗️ 架构审查": architecture,
    }

    for title, findings in all_domain_findings.items():
        if findings:
            report_parts.append(f"## {title} ({len(findings)} 个问题)\n")
            for f in findings:
                sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}
                emoji = sev_emoji.get(f.get("severity", "info"), "⚪")
                report_parts.append(
                    f"### {emoji} {f.get('title', '未命名')}\n"
                    f"- **文件**: `{f.get('file', 'N/A')}`\n"
                    f"- **行号**: {f.get('lines', 'N/A')}\n"
                    f"- **严重程度**: {f.get('severity', 'N/A')}\n"
                    f"- **描述**: {f.get('description', 'N/A')}\n"
                    f"- **建议**: {f.get('suggestion', 'N/A')}\n"
                )
        else:
            report_parts.append(f"## {title}\n✅ 未发现问题\n")

    # 冲突解决结果
    if conflicts:
        report_parts.append("---\n## ⚔️ Agent 辩论结果\n")

        resolved_conflicts = [c for c in conflicts if c.get("status") == "resolved"]
        escalated_conflicts = [c for c in conflicts if c.get("status") == "escalated"]

        if resolved_conflicts:
            report_parts.append(f"### ✅ 已达成共识 ({len(resolved_conflicts)} 个)\n")
            for c in resolved_conflicts:
                report_parts.append(
                    f"- **文件**: `{c.get('file', '')}` (行 {c.get('lines', '')})\n"
                    f"  - 各方立场: {list(c.get('positions', {}).keys())}\n"
                    f"  - 裁决: {c.get('resolution', '')}\n"
                    f"  - 理由: {c.get('reasoning', '')}\n"
                )

        if escalated_conflicts:
            report_parts.append(f"\n### 🔺 需人工裁决 ({len(escalated_conflicts)} 个)\n")
            for c in escalated_conflicts:
                report_parts.append(
                    f"- **文件**: `{c.get('file', '')}` (行 {c.get('lines', '')})\n"
                    f"  - 各方立场 (辩论 {c.get('debate_rounds', 0)} 轮后未达成共识):\n"
                )
                for domain, pos in c.get("positions", {}).items():
                    report_parts.append(f"    - **{domain}**: {pos}\n")

    report = "".join(report_parts)

    # ── 结构化 Fixer Payload（给下游 Agent 用）──
    fixer_payload = _build_fixer_payload(
        all_findings=(security + performance + architecture),
        conflicts=conflicts,
        pr_title=state.get("pr_title", ""),
        review_mode=mode,
    )

    return {"final_report": report, "fixer_payload": fixer_payload}


def _build_fixer_payload(
    all_findings: list[dict],
    conflicts: list[dict],
    pr_title: str,
    review_mode: str,
) -> str:
    """
    构建下游 Agent 可直接消费的结构化修复指令
    
    格式设计原则：
    1. 纯 JSON，去掉所有 Markdown 格式
    2. 按严重程度排序（critical → info）
    3. 每个 issue 只包含执行修复所需的最小信息
    4. 已冲突裁决的 issue 带上最终决议
    """
    import json as json_mod

    # 构建已解决的冲突映射 {file:lines → resolution}
    resolved_map = {}
    for c in conflicts:
        if c.get("status") == "resolved":
            key = f"{c.get('file', '')}:{c.get('lines', '')}"
            resolved_map[key] = c.get("resolution", "")

    # 构建 issue 列表
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    issues = []
    for f in all_findings:
        key = f"{f.get('file', '')}:{f.get('lines', '')}"
        issue = {
            "file": f.get("file", ""),
            "lines": f.get("lines", ""),
            "severity": f.get("severity", "info"),
            "title": f.get("title", ""),
            "fix": f.get("suggestion", ""),
            "domain": f.get("domain", ""),
        }
        # 如果有辩论裁决，用裁决替代原始建议
        if key in resolved_map:
            issue["fix"] = resolved_map[key]
            issue["debated"] = True
        issues.append(issue)

    issues.sort(key=lambda x: severity_order.get(x["severity"], 99))

    payload = {
        "meta": {
            "pr_title": pr_title,
            "review_mode": review_mode,
            "total_issues": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "high_count": sum(1 for i in issues if i["severity"] == "high"),
            "format_version": "1.0",
            "target": "fixer_agent",
        },
        "issues": issues,
    }

    return json_mod.dumps(payload, ensure_ascii=False, indent=2)


# ============================================================
# 构建 LangGraph
# ============================================================

def build_debate_graph() -> StateGraph:
    """
    构建辩论式多智能体审查图
    
    Returns:
        编译后的 StateGraph
    """
    graph = StateGraph(DebateState)

    # 注册节点
    graph.add_node("route_pr", route_pr)
    graph.add_node("review_node", review_node)
    graph.add_node("merge_findings", merge_findings)
    graph.add_node("detect_conflicts", detect_conflicts_node)
    graph.add_node("debate_round", debate_round)
    graph.add_node("escalate", escalate_to_human)
    graph.add_node("generate_report", generate_report)

    # 边
    graph.set_entry_point("route_pr")

    # 分级路由 → 并行审查 (使用 Send API 的条件边)
    graph.add_conditional_edges(
        "route_pr",
        continue_to_reviews,
        path_map=["review_node"],
    )

    # 审查 → 汇聚
    graph.add_edge("review_node", "merge_findings")

    # 汇聚 → 冲突检测
    graph.add_edge("merge_findings", "detect_conflicts")

    # 冲突检测 → 辩论 或 直接生成报告
    graph.add_conditional_edges(
        "detect_conflicts",
        decide_after_detect,
        {
            "debate_round": "debate_round",
            "generate_report": "generate_report",
        },
    )

    # 辩论 → 检查是否继续
    graph.add_conditional_edges(
        "debate_round",
        decide_after_debate,
        {
            "debate_round": "debate_round",
            "escalate": "escalate",
            "generate_report": "generate_report",
        },
    )

    # 升级 → 生成报告
    graph.add_edge("escalate", "generate_report")

    # 报告 → 结束
    graph.add_edge("generate_report", END)

    return graph.compile()


# 编译全局图实例
debate_graph = build_debate_graph()
