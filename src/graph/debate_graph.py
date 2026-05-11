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
    
    ⚡ 三层过滤：
    - Linter 静态分析（语法模式，<1s）
    - Skills Cache 确定性匹配（逻辑模式，<1ms）  
    - Agent LLM 审查（前两层覆盖不了的推理）
    """
    domain = state.get("domain", "security")
    diff = state["pr_diff"]
    files = state["pr_files"]

    # 截断过大的 diff
    from src.tools.code_analyzer import truncate_diff
    diff = truncate_diff(diff, max_lines=600)

    diff_lines = diff.split("\n")

    # ── 还原纯代码（给 Linter + Skills Cache 用）──
    code_lines = []
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            code_lines.append(line[1:])
        elif not line.startswith("-") and not line.startswith("---") and not line.startswith("diff ") and not line.startswith("@@"):
            code_lines.append(line)
    code = "\n".join(code_lines)

    # ── 第 1 层：Linter 静态分析 ──
    linter_prompt = ""
    cache_prompt = ""
    cache_findings = []

    if domain == "security":  # 只跑一次
        try:
            from src.tools.linter_runner import run_multi_linter, linter_results_to_prompt
            linter_results = run_multi_linter(code, files)
            linter_prompt = linter_results_to_prompt(linter_results)
        except Exception:
            pass

        # ── 第 2 层：Skills Cache 确定性匹配 ──
        try:
            from src.tools.pattern_matcher import match_code, build_cache_injection
            cache_findings, handled_lines = match_code(code, diff_lines)
            cache_prompt = build_cache_injection(cache_findings)
        except Exception:
            pass

    # ── 第 3 层：Skills 知识库注入（给 Agent 参考）──
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

    # 注入 Linter + Skills Cache + Skills 到 Agent
    extra_prompts = []
    if linter_prompt:
        extra_prompts.append(linter_prompt)
    if cache_prompt:
        extra_prompts.append(cache_prompt)
    if skill_prompt:
        extra_prompts.append(skill_prompt)

    if extra_prompts:
        agent.system_prompt = agent.system_prompt + "\n".join(extra_prompts)

    findings = await agent.review(diff, files)

    # Skills Cache 命中的结果追加到 findings（不走 LLM 直接加入）
    if cache_findings:
        findings = cache_findings + findings

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
    """只有对抗性冲突时才进辩论，正交发现直接进报告"""
    conflicts = state.get("conflicts", [])
    adversarial = [c for c in conflicts if c.get("adversarial") != False]
    if adversarial:
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
    节点 7：生成最终审查报告（按严重程度排序，融合所有来源）
    """
    security = state.get("security_findings", [])
    performance = state.get("performance_findings", [])
    architecture = state.get("architecture_findings", [])
    conflicts = state.get("conflicts", [])
    debate_round = state.get("debate_round", 0)
    mode = state.get("review_mode", "fast")
    all_findings = security + performance + architecture

    # ── 统计 ──
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    cache_count = 0
    agent_count = 0
    for f in all_findings:
        sev_counts[f.get("severity", "low")] = sev_counts.get(f.get("severity", "low"), 0) + 1
        if f.get("source") == "skills_cache":
            cache_count += 1
        else:
            agent_count += 1

    # ── Linter 结果 ──
    linter_section = ""
    try:
        from src.tools.linter_runner import run_multi_linter, linter_results_to_prompt
        diff = state.get("pr_diff", "")
        code_lines = []
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                code_lines.append(line[1:])
            elif not line.startswith("-") and not line.startswith("---") and not line.startswith("diff ") and not line.startswith("@@"):
                code_lines.append(line)
        code = "\n".join(code_lines)
        lr = run_multi_linter(code, state.get("pr_files", []))
        linter_section = linter_results_to_prompt(lr) or ""
    except Exception:
        pass

    # ── Skills 列表 ──
    skills_list = ""
    default_file = (state.get("pr_files") or ["unknown"])[0] if state.get("pr_files") else "unknown"
    _fix = lambda f: f if f and f != "see diff" else default_file

    # ── 正交交叉发现 ──
    orthogonal_section = ""
    try:
        from src.tools.code_analyzer import detect_conflicts
        orthogonal = getattr(detect_conflicts, '_last_orthogonal', [])
        if orthogonal:
            orthogonal_section = f"\n\n---\n## 🔗 Agent 交叉发现（互补，无需辩论）\n\n> {len(orthogonal)} 处代码被多个 Agent 从不同角度关注。\n\n"
            for c in orthogonal[:8]:
                f = _fix(c.get('file',''))
                da = c.get('domain_a','?')
                db = c.get('domain_b','?')
                orthogonal_section += f"- `{f}` — {da} + {db} 共同关注\n"
    except Exception:
        pass

    # ── Skills 列表 ──
    skills_list = ""
    try:
        from src.tools.skills_loader import load_skills_for_files
        skills = load_skills_for_files(state.get("pr_files", []))
        if skills:
            skills_list = ", ".join(skills.keys())
    except Exception:
        pass

    # ============ 生成报告 ============
    total = len(all_findings)
    critic = sev_counts.get("critical", 0)
    high = sev_counts.get("high", 0)
    mid = sev_counts.get("medium", 0)
    low = sev_counts.get("low", 0)

    report = f"""# 🔍 代码审查报告

## 📊 总览

| 项目 | 详情 |
|------|------|
| PR | {state.get('pr_title', 'N/A')} |
| 审查模式 | {mode}（{len(state.get('active_domains',[]))} Agent） |
| 总问题 | {total}（🔴{critic} 🟠{high} 🟡{mid} 🟢{low}） |
| 来源 | Skills Cache: {cache_count} | Agent: {agent_count} |
| 辩论 | {debate_round} 轮 | 对抗性冲突: {len([c for c in conflicts if c.get('adversarial')])} |
| 规范 | {skills_list or '—'} |

---
"""

    # ── Linter ──
    if linter_section:
        report += linter_section

    # ── 问题清单（按严重程度排序）──
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sev_labels = {"critical": "🔴 Critical", "high": "🟠 High", "medium": "🟡 Medium", "low": "🟢 Low", "info": "ℹ️ Info"}
    all_findings.sort(key=lambda x: sev_order.get(x.get("severity", "info"), 99))

    current_sev = None
    for f in all_findings:
        sev = f.get("severity", "info")
        if sev != current_sev:
            current_sev = sev
            report += f"\n---\n## {sev_labels.get(sev, sev)}\n"

        source = f.get("source", "agent")
        source_tag = {"skills_cache": "⚡Cache", "agent": "🤖Agent"}.get(source, "🤖Agent")
        domain = f.get("domain", "?")
        file = _fix(f.get("file", "?"))
        lines = f.get("lines", "?")
        title = f.get("title", "未命名")
        fix = f.get("suggestion", f.get("fix", "—"))
        desc = f.get("description", "")[:200]

        report += f"\n### {title}\n"
        report += f"- **位置**: `{file}`:{lines} | **来源**: {source_tag} | **领域**: {domain}\n"
        if desc:
            report += f"- **描述**: {desc}\n"
        report += f"- **修复**: {fix}\n"

    # ── 辩论 ──
    adversarial = [c for c in conflicts if c.get("adversarial")]
    if adversarial:
        report += "\n---\n## ⚔️ 辩论裁决\n"
        resolved = [c for c in adversarial if c.get("status") == "resolved"]
        escalated = [c for c in adversarial if c.get("status") == "escalated"]
        if resolved:
            report += f"### ✅ 已裁决 ({len(resolved)})\n"
            for c in resolved[:5]:
                f = _fix(c.get('file',''))
                da = c.get('domain_a','?')
                db = c.get('domain_b','?')
                report += f"- `{f}` — {da} vs {db}\n"
        if escalated:
            report += f"\n### 🔺 需人工裁决 ({len(escalated)})\n"
            for c in escalated:
                report += f"- `{c.get('file','')}` : 辩论 {c.get('debate_rounds',0)} 轮未共识\n"

    # ── 正交 ──
    if orthogonal_section:
        report += orthogonal_section

    # ── 质量校验 ──
    try:
        from src.tools.quality_validator import build_quality_report
        quality = build_quality_report(all_findings, state.get("pr_files", []))
        if quality:
            report += quality
    except Exception:
        pass

    return {"final_report": report}


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
