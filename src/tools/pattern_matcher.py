"""
Skills Cache — 确定性匹配引擎

思路：Skills 文件中定义的 YAML 规则经人工确认 100% 准确，
匹配到直接返回 fix 结论，跳过 LLM 调用。

与 Linter 的区别：
  Linter: 外部程序，规则预定义，只给"可疑"标记
  Skills Cache: 项目内部规则，人确认过的，直接给"修复方案"并跳过 Agent

与 Memory 的区别：
  Memory: 机器自动积累，有误召回风险 → 注入 prompt 让 Agent 确认
  Skills Cache: 人确认过，100% 确定 → 直接出结果
"""
import re
import yaml
from pathlib import Path
from typing import List, Tuple, Optional

SKILLS_ROOT = Path(__file__).parent.parent.parent / "skills"

# 缓存已解析的规则（避免每次审查都解析 YAML）
_rules_cache: Optional[List[dict]] = None


def load_rules() -> List[dict]:
    """
    从 skills/*.md 文件中提取 YAML rules 段
    
    每个 skill 文件的底部有 ```yaml rules: ... ``` 块，
    提取后合并为统一的规则列表。
    """
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache

    rules = []
    for md_file in sorted(SKILLS_ROOT.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")

        # 提取 ```yaml ... ``` 块
        yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', content, re.DOTALL)
        for block in yaml_blocks:
            try:
                parsed = yaml.safe_load(block)
                if parsed and "rules" in parsed:
                    for r in parsed["rules"]:
                        r["source_skill"] = md_file.stem
                        rules.append(r)
            except Exception:
                continue

    _rules_cache = rules
    return rules


def match_code(code: str, diff_lines: List[str]) -> Tuple[List[dict], set]:
    """
    用 Skills 规则匹配代码
    
    Args:
        code: 纯代码文本
        diff_lines: diff 的原始行列表（用于标记已处理的行号范围）
    
    Returns:
        (matched_findings, handled_lines)
        - matched_findings: 命中规则的结果列表
        - handled_lines: 已被处理的行号集合（供后续流程跳过）
    """
    rules = load_rules()
    if not rules:
        return [], set()

    findings = []
    handled_lines = set()

    for rule in rules:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            continue

        # 匹配所有命中位置
        for match in regex.finditer(code):
            # 计算行号（从代码文本中定位）
            before = code[:match.start()]
            line_no = before.count("\n") + 1

            # 匹配行附近的 diff 行号
            for i, dline in enumerate(diff_lines):
                if dline.startswith("+") and not dline.startswith("+++"):
                    if match.group(0).strip() in dline[1:].strip() or dline[1:].strip() in match.group(0):
                        handled_lines.add(i)
                        break

            findings.append({
                "file": "see diff",
                "lines": str(line_no),
                "severity": rule.get("severity", "medium"),
                "title": rule.get("title", "Skills Cache 命中"),
                "description": f"Skills 规则命中: {rule.get('pattern', '')}",
                "suggestion": rule.get("fix", ""),
                "domain": rule.get("source_skill", "skills"),
                "source": "skills_cache",     # ← 标记来源
                "skip_llm": True,             # ← 标记跳过 LLM
            })

    return findings, handled_lines


def build_cache_injection(findings: List[dict]) -> str:
    """
    构建 Agent prompt 中告知"以下问题已由 Skills Cache 处理"的文本
    
    Agent 看到这些后，跳过对应代码区域，聚焦剩余审查。
    """
    if not findings:
        return ""

    lines = [
        "\n\n---\n## ⚡ Skills Cache 确定性命中（以下问题无需 Agent 审查）\n",
        "> 以下问题已由 Skills 规则直接匹配确认，Agent 请跳过对应代码行。\n",
    ]

    by_severity = {"critical": [], "high": [], "medium": [], "low": []}
    for f in findings:
        sev = f.get("severity", "medium")
        if sev in by_severity:
            by_severity[sev].append(f)

    emoji_map = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

    for sev in ["critical", "high", "medium", "low"]:
        items = by_severity.get(sev, [])
        if items:
            lines.append(f"\n### {emoji_map[sev]} {sev.upper()} ({len(items)} 个)\n")
            for f in items:
                lines.append(
                    f"- **行 {f['lines']}**: {f['title']}\n"
                    f"  → 修复: {f['suggestion'][:200]}\n"
                )

    lines.append("\n> ⚡ 以上问题由 Skills Cache 直接判定，Agent 无需重复审查。\n")

    return "".join(lines)


def invalidate_cache():
    """清除缓存（skills 文件更新后调用）"""
    global _rules_cache
    _rules_cache = None
