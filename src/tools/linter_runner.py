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
