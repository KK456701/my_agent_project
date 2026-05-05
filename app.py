"""
主入口 — 辩论式多智能体代码审查系统

用法：
    # CLI 模式：审查一个 diff 文件
    python app.py --diff demo/sample_pr.diff

    # Web 模式：启动 API 服务
    python app.py --serve

    # 通过 GitHub PR URL 审查
    python app.py --pr https://github.com/owner/repo/pull/123
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from src.graph.debate_graph import debate_graph
from src.graph.state import DebateState
from src.tools.code_analyzer import parse_diff_to_files
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


async def review_diff(diff_text: str, title: str = "", output_file: str = "", no_stream: bool = False, commit_message: str = "") -> str:
    """
    核心审查函数：输入 diff，流式输出 Markdown 报告
    
    Args:
        diff_text: git diff 内容
        title: PR 标题
        output_file: 输出文件路径（为空则自动生成）
        no_stream: 是否禁用流式输出（默认 False = 流式）
    
    Returns:
        Markdown 格式的审查报告
    """
    # 验证配置
    config.validate()

    from src.tools.code_analyzer import count_diff_lines, count_diff_files
    from src.tools.smart_router import smart_route
    files = parse_diff_to_files(diff_text)
    total_changed = count_diff_lines(diff_text)
    total_files = count_diff_files(diff_text)

    # ── 路由预览（使用 smart_router 与 graph 内保持一致）──
    preview_mode, preview_reason = smart_route(
        changed_lines=total_changed,
        changed_files=total_files,
        files=files,
        commit_message=commit_message,
        fast_track_max_lines=config.FAST_TRACK_MAX_LINES,
    )
    mode_labels = {"fast": "⚡ 快速通道 (1 Agent)", "dual": "🔶 标准模式 (2 Agent)", "full": "🔥 深度模式 (3 Agent)"}

    console.print(Panel.fit(
        f"[bold cyan]🚀 启动多智能体辩论式代码审查[/]\n"
        f"[dim]变动: {total_changed} 行 / {total_files} 个文件 → {mode_labels.get(preview_mode.value, preview_mode.value)}[/]\n"
        f"[dim]{preview_reason}[/]",
        style="bold cyan"
    ))

    initial_state: DebateState = {
        "pr_title": title or "代码审查",
        "pr_diff": diff_text,
        "pr_files": files,
        "commit_message": commit_message,
        "review_mode": "",
        "route_reason": "",
        "active_domains": [],
        "security_findings": [],
        "performance_findings": [],
        "architecture_findings": [],
        "conflicts": [],
        "debate_round": 0,
        "debate_history": [],
        "final_report": "",
        "fixer_payload": "",
        "escalated": False,
        "total_tokens": 0,
        "error": "",
    }

    # ── 流式执行 ──
    if no_stream:
        final_state = await debate_graph.ainvoke(initial_state)
        report = final_state.get("final_report", "审查失败，未生成报告")
    else:
        report = await _stream_review(initial_state)

    # 自动保存报告（双格式）
    _save_report(report, output_file, title)
    _save_fixer_payload(final_state.get("fixer_payload", ""), title)

    # 🧠 归档到 Markdown 记忆库
    try:
        from src.tools.review_memory import save_review_to_memory, get_memory_stats
        memory_file = save_review_to_memory(report, diff_text, title)
        stats = get_memory_stats()
        console.print(f"[dim]🧠 记忆库: {stats['pattern_files']} 个模式 / {stats['review_files']} 份报告 / {stats['total_cases']} 个案例[/]")
    except Exception:
        pass  # 记忆归档失败不影响主流程

    return report


async def _stream_review(initial_state: DebateState) -> str:
    """
    流式执行审查图，实时展示每个节点的进度
    
    LangGraph astream 会在每个节点完成后 yield 当前状态更新，
    我们据此显示进度。
    """
    import time
    start_time = time.time()

    agent_emoji = {
        "security": "🛡️",
        "performance": "⚡",
        "architecture": "🏗️",
        "consensus": "⚖️",
    }
    domain_cn = {
        "security": "安全检查",
        "performance": "性能分析",
        "architecture": "架构审查",
    }

    node_labels = {
        "route_pr": "📋 分级路由中...",
        "merge_findings": "🔄 汇聚审查结果...",
        "detect_conflicts": "🔍 检测 Agent 冲突...",
        "debate_round": "⚔️ Agent 辩论中...",
        "escalate": "🔺 升级给人工审查...",
        "generate_report": "📝 生成审查报告...",
    }

    final_report = ""

    async for chunk in debate_graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            # ── 审查节点（Send 并行，每个 Agent 完成时触发）──
            if node_name == "review_node":
                domain = node_output.get("domain", "?")
                findings = []
                for key in ("security_findings", "performance_findings", "architecture_findings"):
                    if key in node_output:
                        findings = node_output[key]
                        domain = key.replace("_findings", "")
                        break

                emoji = agent_emoji.get(domain, "🤖")
                cn = domain_cn.get(domain, domain)
                count = len(findings) if isinstance(findings, list) else 0
                elapsed = time.time() - start_time

                if count > 0:
                    console.print(f"  {emoji} [bold]{cn}[/] 完成 → 发现 [bold red]{count}[/] 个问题 ([dim]{elapsed:.1f}s[/])")
                else:
                    console.print(f"  {emoji} [bold]{cn}[/] 完成 → [green]未发现问题[/] ([dim]{elapsed:.1f}s[/])")

            # ── 路由节点 ──
            elif node_name == "route_pr":
                mode = node_output.get("review_mode", "?")
                domains = node_output.get("active_domains", [])
                reason = node_output.get("route_reason", "")
                mode_map = {"fast": "⚡ 快速通道", "dual": "🔶 标准模式", "full": "🔥 深度模式"}
                console.print(f"  📋 路由决策: {mode_map.get(mode, mode)} → 启动 {len(domains)} 个 Agent")
                if reason:
                    console.print(f"     [dim]理由: {reason}[/]")

            # ── 辩论节点 ──
            elif node_name == "debate_round":
                conflicts = node_output.get("conflicts", [])
                resolved = sum(1 for c in conflicts if c.get("status") == "resolved")
                pending = sum(1 for c in conflicts if c.get("status") not in ("resolved", "escalated"))
                round_num = node_output.get("debate_round", "?")
                console.print(f"  ⚔️ 辩论第 {round_num} 轮: [green]{resolved} 个已解决[/] | [yellow]{pending} 个待定[/]")

            # ── 升级节点 ──
            elif node_name == "escalate":
                console.print(f"  [bold red]🔺 {len(node_output.get('conflicts', []))} 个冲突升级给人工[/]")

            # ── 生成报告 ──
            elif node_name == "generate_report":
                final_report = node_output.get("final_report", "")
                total_time = time.time() - start_time
                console.print(f"  [bold green]✅ 审查完成 ({total_time:.1f}s)[/]")

            # ── 其他节点 ──
            elif node_name in node_labels:
                console.print(f"  {node_labels[node_name]}")

    return final_report


async def review_from_github(pr_url: str, no_stream: bool = False) -> str:
    """
    从 GitHub PR URL 获取 diff 并审查
    """
    from src.tools.github_tool import GitHubPRTool

    # 解析 URL: https://github.com/owner/repo/pull/123
    parts = pr_url.rstrip("/").split("/")
    if len(parts) < 7:
        raise ValueError(f"无效的 GitHub PR URL: {pr_url}")

    owner = parts[-4]
    repo = parts[-3]
    pr_number = int(parts[-1])

    github = GitHubPRTool()
    pr_data = await github.get_pr_diff(owner, repo, pr_number)

    console.print(f"[cyan]获取 PR: {owner}/{repo}#{pr_number}")
    console.print(f"[cyan]标题: {pr_data['title']}")

    return await review_diff(pr_data["diff"], pr_data["title"], no_stream=no_stream, commit_message=pr_data.get("body", ""))


def main():
    parser = argparse.ArgumentParser(
        description="🔍 多智能体辩论式代码审查系统"
    )
    parser.add_argument(
        "--diff",
        type=str,
        help="Git diff 文件路径或直接传入 diff 内容",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="直接审查一个 Python 文件（自动包装为 diff 格式）",
    )
    parser.add_argument(
        "--pr",
        type=str,
        help="GitHub PR URL，如 https://github.com/owner/repo/pull/123",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="以 Web API 模式启动",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Web 服务端口 (默认 8000)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="将审查报告保存到指定文件（默认自动保存到 reports/ 目录）",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="禁用流式输出，等待完成后一次性显示结果",
    )
    parser.add_argument(
        "--commit", "-m",
        type=str,
        default="",
        help="Commit 信息（用于智能路由，如 'hotfix: fix login bug'）",
    )

    args = parser.parse_args()

    if args.serve:
        # Web 模式
        import uvicorn
        console.print("[green]🌐 启动 Web API 服务...")
        console.print(f"[green]📡 http://localhost:{args.port}/docs")
        # 动态导入 FastAPI app（延迟导入，避免 CLI 模式需要装 fastapi）
        from app_web import app
        uvicorn.run(app, host="0.0.0.0", port=args.port)
        return

    if args.pr:
        # GitHub PR 模式
        report = asyncio.run(review_from_github(args.pr, no_stream=args.no_stream, commit_message=args.commit))
        console.print(Markdown(report))
        _save_report(report, args.output, "")
        return

    if args.file:
        # 直接审查 Python 文件（自动包装为 diff）
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[red]文件不存在: {args.file}")
            return
        code = file_path.read_text(encoding="utf-8")
        diff_text = _generate_fake_diff(code, file_path.name)
        report = asyncio.run(review_diff(diff_text, file_path.name, args.output, args.no_stream, args.commit))
        console.print(Markdown(report))
        return

    if args.diff:
        # Diff 文件模式
        diff_path = Path(args.diff)
        if diff_path.exists():
            diff_text = diff_path.read_text(encoding="utf-8")
        else:
            diff_text = args.diff  # 直接传入的 diff 字符串

        title = diff_path.stem if diff_path.exists() else "手动输入"
        report = asyncio.run(review_diff(diff_text, title, args.output, args.no_stream, args.commit))
        console.print(Markdown(report))
        return

    # 无参数 → Demo 模式
    console.print("[yellow]未提供参数，运行 Demo 模式...")
    demo_path = Path(__file__).parent / "demo" / "sample_pr.py"
    if demo_path.exists():
        # 用 demo 文件内容模拟一个 diff
        code = demo_path.read_text(encoding="utf-8")
        diff_text = _generate_fake_diff(code)
        report = asyncio.run(review_diff(diff_text, "Demo: 用户登录模块", args.output, args.no_stream, args.commit))
        console.print(Markdown(report))
    else:
        console.print("[red]请使用 --diff 或 --pr 参数指定审查目标")


def _save_report(report: str, output_file: str = "", title: str = "") -> str:
    """
    保存报告到文件
    
    Args:
        report: Markdown 报告内容
        output_file: 用户指定的输出路径（为空则自动生成）
        title: PR 标题（用于自动命名）
    
    Returns:
        保存的文件路径
    """
    import datetime

    if output_file:
        filepath = Path(output_file)
    else:
        # 自动生成文件名：reports/2026-05-04_143052_用户登录模块.md
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_title = title.replace("/", "_").replace("\\", "_").replace(":", "_").replace(" ", "_")[:30] if title else "review"
        filepath = reports_dir / f"{timestamp}_{safe_title}.md"

    filepath.write_text(report, encoding="utf-8")
    console.print(f"\n[green]📄 报告已保存到: {filepath}")

    return str(filepath)


def _save_fixer_payload(payload: str, title: str = "") -> str:
    """
    保存结构化修复指令（给下游 Fixer Agent 消费）
    
    与 Markdown 报告对应，文件名加 _fixer.json 后缀
    """
    import datetime

    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_title = title.replace("/", "_").replace("\\", "_").replace(":", "_").replace(" ", "_")[:30] if title else "review"
    filepath = reports_dir / f"{timestamp}_{safe_title}_fixer.json"

    filepath.write_text(payload, encoding="utf-8")
    console.print(f"[dim]🤖 Fixer Payload 已保存到: {filepath}[/]")

    return str(filepath)


def _generate_fake_diff(code: str, filename: str = "demo/sample_pr.py") -> str:
    """将代码文件包装成 diff 格式（用于演示和 --file 模式）"""
    lines = code.strip().split("\n")
    diff_lines = [
        f"diff --git a/{filename} b/{filename}",
        f"--- a/{filename}",
        f"+++ b/{filename}",
        "@@ -0,0 +1,{} @@".format(len(lines)),
    ]
    for line in lines:
        diff_lines.append(f"+{line}")
    return "\n".join(diff_lines)


if __name__ == "__main__":
    main()
