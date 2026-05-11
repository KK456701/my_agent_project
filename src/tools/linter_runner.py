"""
Linter 集成 — LLM 之前的静态分析层

思路：不等 LLM，先用确定性工具秒出结果
- Ruff: 快速 Python linting
- Bandit: Python 安全漏洞静态扫描

LLM 只审查 linter 覆盖不了的逻辑问题。
Token 省 50%+，准确率还更高。

⚠️ 优雅降级：如果 Ruff/Bandit 未安装，自动跳过，不影响主流程
"""
import subprocess
import json
import sys
import shutil
from pathlib import Path
from typing import Optional


def _find_executable(name: str) -> Optional[str]:
    """查找可执行文件，优先使用当前 venv 中的"""
    # 先尝试 sys.executable -m (适合 venv)
    path = shutil.which(name)
    if path:
        return path
    # 备用：检查 venv Scripts 目录
    venv_dir = Path(sys.executable).parent
    candidate = venv_dir / f"{name}.exe" if sys.platform == "win32" else venv_dir / name
    if candidate.exists():
        return str(candidate)
    return None


def run_python_linter(code: str, filepath: str = "review_target.py") -> dict:
    """
    对代码字符串运行 Ruff + Bandit 静态分析
    
    Args:
        code: 要检查的 Python 代码
        filepath: 虚拟文件名（用于报告中的引用）
    
    Returns:
        {
            "ruff": [{"line": 42, "message": "...", "rule": "F841"}, ...],
            "bandit": [{"line": 24, "message": "...", "severity": "high"}, ...],
            "errors": []
        }
    """
    results = {"ruff": [], "bandit": [], "errors": []}

    # ── Ruff ──
    ruff_path = _find_executable("ruff")
    if ruff_path:
        try:
            proc = subprocess.run(
                [ruff_path, "check", "--output-format", "json", "--stdin-filename", filepath, "-"],
                input=code,
                capture_output=True,
                encoding="utf-8",
                timeout=30,
            )
            if proc.returncode in (0, 1):
                raw = proc.stdout.strip()
                if raw:
                    try:
                        ruff_output = json.loads(raw)
                    except json.JSONDecodeError:
                        ruff_output = []
                    for issue in ruff_output:
                        loc = issue.get("location") or {}
                        results["ruff"].append({
                            "line": loc.get("row", "?"),
                            "column": loc.get("column", "?"),
                            "message": issue.get("message", ""),
                            "rule": issue.get("code", ""),
                            "fixable": (issue.get("fix") or {}).get("applicability", "no"),
                        })
        except Exception as e:
            results["errors"].append(f"Ruff failed: {e}")
    else:
        results["errors"].append("Ruff 未安装（pip install ruff）")

    # ── Bandit (安全检查) ──
    bandit_path = _find_executable("bandit")
    if bandit_path:
        try:
            # Bandit 不支持 stdin，写临时文件
            tmp_file = Path(filepath)
            tmp_file.write_text(code, encoding="utf-8")

            proc = subprocess.run(
                [bandit_path, "-f", "json", "-q", str(tmp_file)],
                capture_output=True,
                encoding="utf-8",
                timeout=30,
            )
            tmp_file.unlink(missing_ok=True)

            if proc.returncode in (0, 1):
                bandit_output = json.loads(proc.stdout) if proc.stdout.strip() else {}
                for issue in bandit_output.get("results", []):
                    results["bandit"].append({
                        "line": issue.get("line_number", "?"),
                        "message": issue.get("issue_text", ""),
                        "severity": issue.get("issue_severity", "medium"),
                        "confidence": issue.get("issue_confidence", "medium"),
                        "cwe": issue.get("test_id", ""),
                    })
        except Exception as e:
            results["errors"].append(f"Bandit failed: {e}")
    else:
        results["errors"].append("Bandit 未安装（pip install bandit）")

    return results


def detect_language(files: list[str]) -> str:
    """
    根据文件扩展名检测主要语言
    
    Returns: "python" | "javascript" | "go" | "unknown"
    """
    for f in files:
        ext = Path(f).suffix.lower()
        if ext in (".py",):
            return "python"
        if ext in (".js", ".jsx", ".ts", ".tsx"):
            return "javascript"
        if ext in (".go",):
            return "go"
    return "unknown"


def run_multi_linter(code: str, files: list[str], filepath: str = "review_target") -> dict:
    """
    根据代码语言自动选择 Linter
    
    Args:
        code: 代码文本
        files: 文件路径列表（用于判断语言）
        filepath: 虚拟文件名
    
    Returns:
        和 run_python_linter 相同格式的结果字典
    """
    lang = detect_language(files)

    if lang == "python":
        return run_python_linter(code, f"{filepath}.py")
    elif lang == "javascript":
        return run_js_linter(code, f"{filepath}.js")
    elif lang == "go":
        return run_go_linter(code, f"{filepath}.go")

    return {"ruff": [], "bandit": [], "errors": [f"不支持的语言: {lang}"]}


def run_js_linter(code: str, filepath: str = "review_target.js") -> dict:
    """
    对 JavaScript/TypeScript 代码运行 ESLint 静态分析
    
    ⚠️ 需要: npm install -g eslint (跳过不影响主流程)
    """
    results = {"ruff": [], "bandit": [], "errors": []}

    eslint_path = _find_executable("eslint")
    if not eslint_path:
        results["errors"].append("ESLint 未安装（npm install -g eslint）")
        return results

    try:
        # 写临时文件
        tmp_file = Path(filepath)
        tmp_file.write_text(code, encoding="utf-8")

        proc = subprocess.run(
            [eslint_path, "--format", "json", str(tmp_file)],
            capture_output=True, encoding="utf-8", timeout=30,
        )
        tmp_file.unlink(missing_ok=True)

        if proc.stdout.strip():
            try:
                eslint_output = json.loads(proc.stdout)
                for file_result in eslint_output:
                    for msg in file_result.get("messages", []):
                        sev = "medium" if msg.get("severity") == 2 else "low"
                        results["ruff"].append({
                            "line": msg.get("line", "?"),
                            "message": msg.get("message", ""),
                            "rule": msg.get("ruleId", "eslint"),
                        })
            except json.JSONDecodeError:
                pass
    except Exception as e:
        results["errors"].append(f"ESLint failed: {e}")

    return results


def run_go_linter(code: str, filepath: str = "review_target.go") -> dict:
    """
    对 Go 代码运行 golangci-lint 静态分析
    
    ⚠️ 需要: go install golangci-lint (跳过不影响主流程)
    """
    results = {"ruff": [], "bandit": [], "errors": []}

    golangci_path = _find_executable("golangci-lint")
    if not golangci_path:
        results["errors"].append("golangci-lint 未安装（go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest）")
        return results

    try:
        tmp_file = Path(filepath)
        tmp_file.write_text(code, encoding="utf-8")

        proc = subprocess.run(
            [golangci_path, "run", "--out-format", "json", str(tmp_file)],
            capture_output=True, encoding="utf-8", timeout=30,
        )
        tmp_file.unlink(missing_ok=True)

        if proc.stdout.strip():
            try:
                issues = json.loads(proc.stdout).get("Issues", [])
                for iss in issues:
                    results["ruff"].append({
                        "line": iss.get("Pos", {}).get("Line", "?"),
                        "message": iss.get("Text", ""),
                        "rule": iss.get("FromLinter", "golangci"),
                    })
            except json.JSONDecodeError:
                pass
    except Exception as e:
        results["errors"].append(f"golangci-lint failed: {e}")

    return results


def linter_results_to_prompt(linter_results: dict) -> str:
    """
    将 Linter 结果格式化为可注入 Agent prompt 的文本
    
    Returns:
        Markdown 格式的摘要（空字符串 = 无问题或 linter 不可用）
    """
    ruff = linter_results.get("ruff", [])
    bandit = linter_results.get("bandit", [])
    errors = linter_results.get("errors", [])

    if not ruff and not bandit:
        if errors and all("未安装" in e for e in errors):
            return ""  # 工具未安装 → 静默跳过
        return ""

    parts = ["\n\n---\n## 🔧 静态分析结果（Linter 秒出，无需 LLM）\n"]

    if ruff:
        parts.append(f"\n### Ruff ({len(ruff)} 个问题)\n")
        # 按规则分组
        by_rule = {}
        for r in ruff:
            rule = r["rule"]
            if rule not in by_rule:
                by_rule[rule] = []
            by_rule[rule].append(r)

        for rule, issues in list(by_rule.items())[:10]:  # 限制输出
            sample = issues[0]
            parts.append(
                f"- **{rule}** (×{len(issues)}) — "
                f"行 {sample['line']}: {sample['message'][:120]}\n"
            )

    if bandit:
        parts.append(f"\n### Bandit 安全检查 ({len(bandit)} 个问题)\n")
        for b in bandit[:10]:
            sev = b.get("severity", "medium")
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
            parts.append(
                f"- {emoji} **{b.get('cwe', '?')}** (行 {b['line']}, {sev}) — "
                f"{b['message'][:150]}\n"
            )

    parts.append("\n> ⚡ 以上问题由静态工具直接检出，Agent 请跳过这些，聚焦逻辑审查。\n")

    return "".join(parts)
