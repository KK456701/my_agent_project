"""
CodeGraph PR 分析器 — 一键获取 PR 变更的完整代码图谱

输入: PR diff 或 GitHub PR URL
输出: 变更符号的完整源码 + 调用关系 + 被调用方源码

依赖: CodeGraph CLI 已安装 (codegraph init -i 完成索引)
"""
import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# ============================================================
# 主入口
# ============================================================

class CodeGraphPRAnalyzer:
    """
    PR → CodeGraph 图谱分析

    用法:
        analyzer = CodeGraphPRAnalyzer(project_root="d:/work/testagentPR")
        context = analyzer.analyze_pr(diff_text, pr_files)
        # → 返回结构化的 Markdown 文本，直接注入 Impact Agent
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._ensure_indexed()

    def _ensure_indexed(self):
        """确保项目已用 CodeGraph 索引"""
        db_path = self.project_root / ".codegraph" / "codegraph.db"
        if not db_path.exists():
            print(f"[CodeGraph] 项目未索引，正在初始化...")
            subprocess.run(
                ["codegraph", "init", "-i", str(self.project_root)],
                capture_output=True, text=True, timeout=120
            )

    # ── 主方法：分析整个 PR ──

    def analyze_pr(self, diff_text: str, pr_files: list[str]) -> str:
        """
        分析 PR 的影响范围，返回 Markdown 格式的上下文

        对 diff 中每个变更符号:
        1. 获取完整源码 (codegraph_node)
        2. 获取调用方 + 源码 (codegraph_callers)
        3. 获取被调用方 + 源码 (codegraph_callees)
        4. 分析影响半径 (codegraph_impact)
        """
        symbols = self._extract_changed_symbols(diff_text)
        if not symbols:
            return ""

        sections = ["\n\n---\n## 🔗 代码图谱分析（CodeGraph）\n"]

        for sym in symbols:
            section = self._analyze_symbol(sym)
            if section:
                sections.append(section)

        return "\n".join(sections)

    def _analyze_symbol(self, sym: dict) -> str:
        """分析单个符号，返回 Markdown 段落"""
        name = sym["name"]
        kind = sym["kind"]

        result = f"### `{name}` ({kind}) — {sym['file']}\n\n"

        # 1. 完整源码
        source = self._run("node", [name, "--json"])
        if source:
            code = self._extract_source(source)
            if code:
                result += f"**完整源码**:\n```java\n{code}\n```\n\n"

        # 2. 调用方
        callers = self._run("callers", [name, "--json"])
        if callers:
            result += self._format_callers(callers)

        # 3. 被调用方
        callees = self._run("callees", [name, "--json"])
        if callees:
            result += self._format_callees(callees)

        # 4. 影响分析
        impact = self._run("impact", [name, "--depth", "2", "--json"])
        if impact:
            result += self._format_impact(impact)

        result += "---\n\n"
        return result

    # ── CodeGraph CLI 调用 ──

    def _run(self, command: str, args: list[str]) -> Optional[dict]:
        """调用 CodeGraph CLI，返回 JSON"""
        try:
            result = subprocess.run(
                ["codegraph", command] + args,
                cwd=str(self.project_root),
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except Exception as e:
            print(f"[CodeGraph] {command} 失败: {e}")
        return None

    # ── 格式化输出 ──

    def _extract_source(self, data: dict) -> str:
        """从 codegraph_node 返回中提取源码"""
        if isinstance(data, dict):
            for key in ("source", "code", "content"):
                if key in data:
                    return data[key]
            if "body" in data:
                return data["body"]
        if isinstance(data, list) and len(data) > 0:
            return self._extract_source(data[0])
        return ""

    def _format_callers(self, data: dict) -> str:
        """格式化调用方列表"""
        callers = data.get("callers", data) if isinstance(data, dict) else data
        if isinstance(callers, dict):
            callers = callers.get("items", callers.get("results", []))

        if not callers:
            return "**调用方**: 无\n\n"

        lines = [f"**调用方** ({len(callers)} 处):\n"]
        for c in callers[:5]:
            name = c.get("name", c.get("symbol", "?"))
            file = c.get("file", c.get("path", "?"))
            line = c.get("line", "")
            code = c.get("source", c.get("code", ""))
            loc = f"{file}:{line}" if line else file
            lines.append(f"- `{name}` → `{loc}`")
            if code:
                lines.append(f"  ```\n  {code.strip()[:200]}\n  ```")
        lines.append("")
        return "\n".join(lines)

    def _format_callees(self, data: dict) -> str:
        """格式化被调用方列表"""
        callees = data.get("callees", data) if isinstance(data, dict) else data
        if isinstance(callees, dict):
            callees = callees.get("items", callees.get("results", []))

        if not callees:
            return ""

        lines = [f"**被调用方** ({len(callees)} 处):\n"]
        for c in callees[:5]:
            name = c.get("name", c.get("symbol", "?"))
            lines.append(f"- `{name}`")
        lines.append("")
        return "\n".join(lines)

    def _format_impact(self, data: dict) -> str:
        """格式化影响分析"""
        affected = data.get("affected_count", data.get("count", "?"))
        depth = data.get("depth", "?")
        return f"**影响半径**: {affected} 个符号 (深度 {depth})\n\n"

    # ── 符号提取（从 diff 用正则） ──

    def _extract_changed_symbols(self, diff_text: str) -> list[dict]:
        """从 diff 提取变更符号"""
        symbols = []
        current_file = ""

        for line in diff_text.split("\n"):
            if line.startswith("diff --git "):
                parts = line.split(" ")
                current_file = parts[3][2:] if len(parts) >= 4 else ""
                continue

            if not line.startswith("+") or line.startswith("+++"):
                continue

            code = line[1:].strip()

            # Java: public/private/protected ReturnType methodName(
            m = re.match(
                r'(?:public|private|protected|static|\s)+'
                r'\w+(?:<[^>]*>)?\s+(\w+)\s*\(',
                code
            )
            if m and not code.startswith("//"):
                symbols.append({
                    "name": m.group(1),
                    "kind": "method",
                    "file": current_file,
                })
                continue

            # Python: def xxx( / class xxx
            m = re.match(r'(?:def|class)\s+(\w+)', code)
            if m:
                symbols.append({
                    "name": m.group(1),
                    "kind": "function" if code.startswith("def") else "class",
                    "file": current_file,
                })
                continue

            # Go: func xxx( / func (r *T) xxx(
            m = re.match(r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', code)
            if m:
                symbols.append({
                    "name": m.group(1),
                    "kind": "function",
                    "file": current_file,
                })
                continue

        return symbols


# ============================================================
# 便捷函数：一键获取 PR 影响分析
# ============================================================

def analyze_github_pr(
    owner: str,
    repo: str,
    pr_number: int,
    project_root: str
) -> str:
    """
    一键分析 GitHub PR 的影响范围

    流程: git pull → CodeGraph sync → analyze_pr

    Args:
        owner: 仓库所有者 (如 "KK456701")
        repo: 仓库名 (如 "testagentPR")
        pr_number: PR 编号
        project_root: 本地仓库路径

    Returns:
        Markdown 格式的影响分析上下文
    """
    root = Path(project_root)

    # 确保仓库是最新的
    subprocess.run(["git", "fetch", "origin"], cwd=str(root),
                   capture_output=True, timeout=30)
    subprocess.run(["git", "checkout", "main"], cwd=str(root),
                   capture_output=True, timeout=15)
    subprocess.run(["git", "pull", "origin", "main"], cwd=str(root),
                   capture_output=True, timeout=30)

    # 增量同步 CodeGraph 索引
    subprocess.run(["codegraph", "sync", str(root)],
                   capture_output=True, timeout=30)

    # 获取 PR diff
    from src.tools.github_tool import GitHubPRTool
    import asyncio
    github = GitHubPRTool()
    pr_data = asyncio.run(github.get_pr_diff(owner, repo, pr_number))

    # 分析
    analyzer = CodeGraphPRAnalyzer(str(root))
    return analyzer.analyze_pr(pr_data["diff"], pr_data["files"])
