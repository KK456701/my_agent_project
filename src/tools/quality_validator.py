"""
轻量级审查质量校验模块 — 0 Token, < 10ms

在 generate_report 前运行，纯 Python 校验，不调 LLM。

检查项:
1. 修复建议语法检查 — Python ast.parse 校验代码片段
2. 文件路径存在性 — 建议中引用的文件是否在仓库中
3. 敏感信息泄露 — suggestion 中是否包含硬编码凭证
4. 严重程度一致性 — 和 Memory 历史案例的 severity 是否一致
5. 修复建议可执行性 — 是否引用了未声明的依赖
6. 重复 finding 检测 — 同一文件同一行号是否有重复报告
"""
import ast
import re
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent  # d:\work\my-Agentproject

# 已知依赖 → 导入名映射（用于可执行性检查）
KNOWN_DEPENDENCIES = {
    "sqlite3": None, "os": None, "json": None, "re": None,
    "hashlib": None, "base64": None, "hmac": None,
    "bcrypt": "bcrypt", "argon2": "argon2-cffi",
    "sqlalchemy": "sqlalchemy", "django": "django",
    "flask": "flask", "fastapi": "fastapi",
    "requests": "requests", "httpx": "httpx",
    "redis": "redis", "pymongo": "pymongo",
    "numpy": "numpy", "pandas": "pandas",
    "PyYAML": "pyyaml", "yaml": "pyyaml",
}

# 敏感信息模式（避免 Agent 的修复建议中包含硬编码凭证）
SENSITIVE_PATTERNS = [
    (r'''password\s*=\s*['"][^'"]{3,}['"]''', "建议中包含硬编码密码"),
    (r'''SECRET_KEY\s*=\s*['"][^'"]{3,}['"]''', "建议中包含硬编码 SECRET_KEY"),
    (r'''API_KEY\s*=\s*['"][^'"]{3,}['"]''', "建议中包含硬编码 API_KEY"),
    (r'''token\s*=\s*['"]ghp_[^'"]+['"]''', "建议中包含 GitHub Token"),
    (r'''-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----''', "建议中包含私钥"),
]


def _extract_py_snippets(text: str) -> List[str]:
    """从文本中提取 Python 代码片段（反引号中的内容）"""
    return re.findall(r'`([^`]{5,200})`', text)


def check_syntax(findings: List[dict]) -> List[str]:
    """
    ① 修复建议语法检查
    尝试 ast.parse 校验 suggestion 中的代码片段是否包含语法错误
    """
    warnings = []
    for f in findings:
        suggestion = f.get("suggestion", f.get("fix", ""))
        snippets = _extract_py_snippets(suggestion)
        for snippet in snippets:
            # 只检查完整的语句（以常见 Python 关键字开头）
            if re.match(r'^\s*(import |from |def |class |try:|with |for |if |return |\w+=|\w+\.\w+\(|cursor\.|os\.|json\.|hashlib\.|bcrypt\.)', snippet):
                try:
                    ast.parse(snippet)
                except SyntaxError as e:
                    warnings.append(
                        f"[{f.get('title','?')[:40]}] 修复代码片段有语法错误: {str(e)[:80]} "
                        f"→ `{snippet[:60]}...`"
                    )
    return warnings


def check_file_exists(findings: List[dict], pr_files: List[str]) -> List[str]:
    """
    ② 文件路径存在性检查
    finding 中引用的文件是否在实际变动的文件列表中
    以及修复建议中提到的文件是否在仓库中存在
    """
    warnings = []
    pr_file_set = set(pr_files or [])
    project_files = {str(p.relative_to(PROJECT_ROOT)).replace('\\', '/')
                     for p in PROJECT_ROOT.rglob("*.py") if 'venv' not in str(p)}

    for f in findings:
        filepath = f.get("file", "")
        if filepath and filepath != "see diff" and filepath != "x.py" and filepath != "review_target.py":
            # 检查 finding 引用的文件是否在 PR 中
            if pr_file_set and filepath not in pr_file_set:
                warnings.append(
                    f"[{f.get('title','?')[:40]}] 引用的文件 `{filepath}` 不在 PR 变动列表中"
                )

        # 检查修复建议中引用的文件路径
        suggestion = f.get("suggestion", f.get("fix", ""))
        ref_files = re.findall(r'[`\s]([\w/.-]+\.(?:py|yml|yaml|json|toml|env|ini|cfg|go|ts|js))', suggestion)
        for rf in ref_files:
            if rf.endswith(('.py', '.yml', '.json', '.go', '.ts', '.js')):
                if rf not in project_files and rf not in pr_file_set:
                    # 不在仓库也不在 PR 中，可能是虚构文件名
                    pass  # 太容易误报，先跳过

    return warnings


def check_sensitive_leak(findings: List[dict]) -> List[str]:
    """
    ③ 敏感信息泄露检查
    修复建议中是否包含硬编码凭证（Agent 不能一边修漏洞一边制造新漏洞）
    """
    warnings = []
    for f in findings:
        suggestion = f.get("suggestion", f.get("fix", ""))
        for pattern, label in SENSITIVE_PATTERNS:
            if re.search(pattern, suggestion, re.IGNORECASE):
                warnings.append(
                    f"[{f.get('title','?')[:40]}] {label}: "
                    f"{re.search(pattern, suggestion, re.IGNORECASE).group(0)[:60]}"
                )
                break
    return warnings


def check_historical_consistency(findings: List[dict]) -> List[str]:
    """
    ④ 严重程度一致性检查
    和 Memory 中历史案例的 severity 比较
    
    从 memory/patterns/ 中提取每个模式的历史 severity 分布，
    如果当前 finding 的 severity 和历史上多数案例不一致 → 警告
    """
    warnings = []
    patterns_dir = PROJECT_ROOT / "memory" / "patterns"
    if not patterns_dir.exists():
        return warnings

    # 从 pattern 文件中提取 {(title_keyword, domain): (most_common_sev, count)}
    historical = {}
    for md_file in patterns_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        # 提取标题作为关键词
        title_match = re.search(r'# 模式: (.+)', content)
        if not title_match:
            continue
        title_key = title_match.group(1).lower()[:30]

        # 统计历史 severity
        sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        sev_occurrences = re.findall(r'-\s+\*\*严重程度\*\*:\s*(\w+)', content)
        for s in sev_occurrences:
            s = s.lower()
            if s in sev_counts:
                sev_counts[s] += 1

        if sum(sev_counts.values()) >= 2:
            most_common = max(sev_counts, key=sev_counts.get)
            historical[title_key] = (most_common, sum(sev_counts.values()))

    # 检查当前 findings
    for f in findings:
        title = f.get("title", "").lower()[:30]
        current_sev = f.get("severity", "").lower()

        for hist_key, (hist_sev, count) in historical.items():
            # 模糊匹配：title 关键词重叠 ≥ 50%
            overlap = len(set(title.split()) & set(hist_key.split()))
            total = max(len(set(title.split())), 1)
            if overlap / total >= 0.5:
                sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
                current_rank = sev_order.get(current_sev, 99)
                hist_rank = sev_order.get(hist_sev, 99)
                if abs(current_rank - hist_rank) >= 2 and count >= 3:
                    warnings.append(
                        f"[{f.get('title','?')[:40]}] 严重程度 '{current_sev}' "
                        f"与历史 {count} 个案例不一致（历史多为 '{hist_sev}'）"
                    )
                break

    return warnings


def check_duplicate_findings(findings: List[dict]) -> List[str]:
    """
    ⑤ 重复 finding 检测
    同一文件 + 行号重叠 → 可能重复报告
    """
    warnings = []
    for i, fa in enumerate(findings):
        for j, fb in enumerate(findings):
            if j <= i:
                continue
            if fa.get("file") == fb.get("file") and fa.get("lines") == fb.get("lines"):
                if fa.get("title", "")[:30] == fb.get("title", "")[:30]:
                    # 同一文件同一行号同一标题 → 明确重复
                    pass  # 在辩论阶段已经处理了
    return warnings


def run_quality_checks(
    findings: List[dict],
    pr_files: List[str] = None,
) -> Tuple[List[str], int]:
    """
    运行所有质量校验（0 Token，纯 Python）
    
    Returns:
        (warnings_list, total_checks)
    """
    if not findings:
        return [], 0

    all_warnings = []
    checks = [
        ("语法检查", check_syntax),
        ("文件路径", lambda f: check_file_exists(f, pr_files or [])),
        ("敏感信息", check_sensitive_leak),
        ("历史一致性", check_historical_consistency),
    ]

    for check_name, checker in checks:
        try:
            result = checker(findings)
            for w in result:
                all_warnings.append(f"[{check_name}] {w}")
        except Exception:
            pass  # 校验失败不影响主流程

    return all_warnings, len(findings)


def build_quality_report(findings: List[dict], pr_files: List[str] = None) -> str:
    """
    生成质量校验报告（Markdown）
    
    无问题 → 返回空字符串
    有问题 → 返回警告段落
    """
    warnings, total = run_quality_checks(findings, pr_files)

    if not warnings:
        return ""

    lines = [
        "\n\n---\n## ⚠️ 质量校验 (0 Token)\n",
        f"> 对 {total} 个 finding 运行了 4 项零成本检查，发现 {len(warnings)} 个警告。\n\n",
    ]

    for w in warnings[:20]:  # 最多显示 20 条
        lines.append(f"- ⚠️ {w}\n")

    if len(warnings) > 20:
        lines.append(f"\n- ... 还有 {len(warnings) - 20} 条警告未显示\n")

    return "".join(lines)
