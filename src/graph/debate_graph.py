"""
LangGraph 审查图 — 多智能体代码审查的核心编排 (v2 无辩论版)

图结构：

    START
      ↓
  [route_pr]          ← 分级路由：fast / dual / full
      ↓
  [parallel_review]   ← 并行审查 (Send API)
      ↓
  [generate_report]   ← 汇聚 + 生成报告 → END
"""
from typing import Literal
import subprocess, json as json_mod
from pathlib import Path
from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from src.graph.state import DebateState
from src.agents.security_agent import SecurityReviewAgent
from src.agents.performance_agent import PerformanceReviewAgent
from src.agents.architecture_agent import ArchitectureReviewAgent
from src.tools.code_analyzer import count_diff_lines, count_diff_files, truncate_diff
from src.tools.smart_router import smart_route, RouteMode
from config import config

# CodeGraph CLI 路径
CG_PATH = r"C:\Users\lenovo\AppData\Local\codegraph\current\bin\codegraph.cmd"


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
        RouteMode.FAST: ["security", "impact"],
        RouteMode.DUAL: ["security", "performance", "impact"],
        RouteMode.FULL: ["security", "performance", "architecture", "impact"],
    }

    # ── 关联性分析全链路 ──
    # ① DeepSeek 筛选需要深挖的变更行
    # ② CodeGraph CLI 查受影响文件
    # ③ 读取受影响文件 + 变更文件完整源码
    # ④ 注入 Impact Agent
    full_file_context = ""
    try:
        project_root = config.PROJECT_ROOT
        if project_root:
            root = Path(project_root)

            # ── 第 1 步：DeepSeek 筛选 ──
            from src.tools.impact_classifier_llm import classify_changes_llm
            skip_list, light_list, deep_list = classify_changes_llm(
                diff, project_root, deep_threshold=1
            )

            # 收集所有需要深挖的符号
            deep_symbols = [d.symbol for d in deep_list if d.symbol]

            # ── 第 2 步：CodeGraph 查受影响文件 ──
            affected_files = set()
            if deep_symbols:
                for symbol in deep_symbols[:5]:  # 最多查 5 个符号
                    try:
                        # 查调用方
                        r = subprocess.run(
                            [CG_PATH, "callers", symbol, "--json"],
                            cwd=str(root), capture_output=True, text=True, timeout=10
                        )
                        if r.returncode == 0:
                            data = json_mod.loads(r.stdout)
                            for c in data.get("callers", []):
                                fp = c.get("filePath", "")
                                if fp:
                                    affected_files.add(fp)

                        # 查影响范围
                        r = subprocess.run(
                            [CG_PATH, "impact", symbol, "--depth", "2", "--json"],
                            cwd=str(root), capture_output=True, text=True, timeout=10
                        )
                        if r.returncode == 0:
                            data = json_mod.loads(r.stdout)
                            for n in data.get("affected", []):
                                fp = n.get("filePath", "")
                                if fp and not fp.endswith((".java", ".py", ".go", ".ts", ".js")):
                                    continue
                                if fp:
                                    affected_files.add(fp)
                    except Exception:
                        continue

            # ── 第 3 步：读取文件完整源码 ──
            parts = []
            MAX_CHARS_PER_FILE = 2500

            # 先放受影响文件
            for f in sorted(affected_files):
                full_path = root / f
                if full_path.exists() and full_path not in [root / x for x in files]:
                    try:
                        content = full_path.read_text(encoding="utf-8", errors="ignore")
                        parts.append(f"### 📎 受影响文件: {f}\n```\n{content[:MAX_CHARS_PER_FILE]}\n```")
                    except Exception:
                        pass

            # 再放变更文件
            for f in files:
                full_path = root / f
                if full_path.exists():
                    try:
                        content = full_path.read_text(encoding="utf-8", errors="ignore")
                        parts.append(f"### 📝 变更文件: {f}\n```\n{content[:MAX_CHARS_PER_FILE]}\n```")
                    except Exception:
                        pass

            if parts:
                # 加筛选摘要
                summary = f"\n> 影响力分级: 跳过 {len(skip_list)} | 轻量 {len(light_list)} | 深挖 {len(deep_list)}"
                if deep_symbols:
                    summary += f"\n> 深挖符号: {', '.join(deep_symbols[:5])}"
                if affected_files:
                    summary += f"\n> CodeGraph 发现 {len(affected_files)} 个受影响文件"
                parts.insert(0, summary)
                full_file_context = "\n\n".join(parts)

    except Exception as e:
        print(f"[ImpactPipeline] 失败: {e}")

    return {
        "review_mode": mode.value,
        "route_reason": reason,
        "active_domains": domain_map[mode],
        "full_file_context": full_file_context,
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
            "full_file_context": state.get("full_file_context", ""),
        }))
    return sends


async def review_node(state: DebateState) -> dict:
    """
    节点 2（可并行执行）：单个 Agent 执行审查
    
    ⚡ 两层过滤：
    - Linter 静态分析（语法模式，<1s）
    - Agent LLM 审查（Linter 覆盖不了的推理）
    """
    domain = state.get("domain", "security")
    diff = state["pr_diff"]
    files = state["pr_files"]

    # 截断过大的 diff
    from src.tools.code_analyzer import truncate_diff
    diff = truncate_diff(diff, max_lines=600)

    diff_lines = diff.split("\n")

    # ── 第 1 层：Linter 静态分析 ──
    linter_prompt = ""

    if domain == "security":  # 只跑一次
        try:
            from src.tools.linter_runner import run_multi_linter, linter_results_to_prompt
            linter_results = run_multi_linter(code, files)
            linter_prompt = linter_results_to_prompt(linter_results)
        except Exception:
            pass

    # ── 第 2 层：Skills 团队规范注入（给 Agent 参考）──
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

    # Impact Agent 有特殊处理（需要代码图谱上下文）
    if domain == "impact":
        from src.agents.impact_agent import ImpactReviewAgent
        agent = ImpactReviewAgent()
        full_ctx = state.get("full_file_context", "")
        findings = await agent.review(diff, files, full_file_context=full_ctx)
        return {"impact_findings": findings}

    agent_cls = agents.get(domain)
    if not agent_cls:
        return {}

    agent = agent_cls()

    # 注入 Linter + Skills 团队规范
    extra_prompts = []
    if linter_prompt:
        extra_prompts.append(linter_prompt)
    if skill_prompt:
        extra_prompts.append(skill_prompt)

    if extra_prompts:
        agent.system_prompt = agent.system_prompt + "\n".join(extra_prompts)

    findings = await agent.review(diff, files)

    # 每个领域的结果写入对应字段
    result_key = f"{domain}_findings"
    return {result_key: findings}


# ── 辩论冲突相关节点已移除 (v2) ——
# detect_conflicts_node, debate_round, decide_after_detect,
# decide_after_debate, escalate_to_human, merge_findings 不再需要


def generate_report(state: DebateState) -> dict:
    """
    节点 3：汇聚所有 Agent 发现 + 生成最终审查报告
    """
    security = state.get("security_findings", [])
    performance = state.get("performance_findings", [])
    architecture = state.get("architecture_findings", [])
    impact = state.get("impact_findings", [])
    mode = state.get("review_mode", "fast")
    all_findings = security + performance + architecture + impact

    # ── 统计 ──
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    cache_count = 0
    agent_count = 0
    for f in all_findings:
        sev = f.get("severity", "low")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
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
    try:
        from src.tools.skills_loader import load_skills_for_files
        skills = load_skills_for_files(state.get("pr_files", []))
        if skills:
            skills_list = ", ".join(skills.keys())
    except Exception:
        pass

    default_file = (state.get("pr_files") or ["unknown"])[0] if state.get("pr_files") else "unknown"
    _fix = lambda f: f if f and f != "see diff" else default_file

    # ============ 生成报告 ============
    total = len(all_findings)
    critic = sev_counts.get("critical", 0)
    high = sev_counts.get("high", 0)
    mid = sev_counts.get("medium", 0)
    low = sev_counts.get("low", 0)
    info = sev_counts.get("info", 0)
    domains = state.get("active_domains", [])

    report = f"""# 🔍 代码审查报告

## 📊 总览

| 项目 | 详情 |
|------|------|
| PR | {state.get('pr_title', 'N/A')} |
| 审查模式 | {mode}（{len(domains)} Agent: {", ".join(domains)}） |
| 总问题 | {total}（🔴{critic} 🟠{high} 🟡{mid} 🟢{low} 💡{info}） |
| 来源 | Skills Cache: {cache_count} | Agent: {agent_count} |
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
    构建多智能体审查图 (v2 无辩论版)

    节点: route_pr → parallel_review → generate_report → END
    """
    graph = StateGraph(DebateState)

    graph.add_node("route_pr", route_pr)
    graph.add_node("review_node", review_node)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("route_pr")

    # 分级路由 → 并行审查
    graph.add_conditional_edges(
        "route_pr",
        continue_to_reviews,
        path_map=["review_node"],
    )

    # 审查完成 → 直接生成报告
    graph.add_edge("review_node", "generate_report")

    # 报告 → 结束
    graph.add_edge("generate_report", END)

    return graph.compile()


# 编译全局图实例
debate_graph = build_debate_graph()
