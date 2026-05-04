"""
Markdown 审查记忆系统 — 零依赖的长期知识库

思路：像 Claude Code 一样用 Markdown 文件做知识存储
- memory/patterns/   → 按问题类型分类的模式知识（如 sql_injection.md）
- memory/reviews/    → 每次审查的完整报告归档

工作流：
  审查前 → 扫描 PR diff → 匹配已知模式 → 注入到 Agent prompt
  审查后 → 提取新发现 → 更新/创建模式文件 → 归档报告
"""
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# 记忆存储根目录
MEMORY_ROOT = Path(__file__).parent.parent.parent / "memory"
PATTERNS_DIR = MEMORY_ROOT / "patterns"
REVIEWS_DIR = MEMORY_ROOT / "reviews"

# ── 召回配置 ──
MAX_PATTERNS_INJECTED = 5        # 最多注入 5 个模式（防止上下文爆炸）
MAX_MEMORY_CHARS = 5000          # 记忆总字符数上限（约 1200 tokens）
PATTERN_SUMMARY_LENGTH = 500     # 每个模式的摘要长度
MIN_KEYWORD_MATCHES = 2          # 最少命中关键词数

# ── 模式文件缓存（避免每次召回都读磁盘）──
_pattern_cache: dict[str, tuple[float, str]] = {}  # filename → (mtime, content)


def _build_dynamic_signatures() -> dict:
    """
    从 memory/patterns/ 目录动态构建签名表
    
    不再依赖硬编码的 PATTERN_SIGNATURES，
    而是从所有 .md 文件中自动提取关键词。
    
    策略：取文件名 + 前 200 字符作为关键词来源
    """
    signatures = {}
    for md_file in PATTERNS_DIR.glob("*.md"):
        name = md_file.stem
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # 从文件名和内容中提取关键词
        keywords = set()

        # 1. 文件名本身就是关键词（如 sql_injection → ["sql", "injection"]）
        for part in re.split(r'[_\-\s]+', name.lower()):
            if len(part) >= 3:
                keywords.add(part)

        # 2. 从内容中提取技术关键词（简单分词，不用复杂正则）
        tech_keywords = [
            "f-string", "execute", "SELECT", "INSERT", "DELETE", "DROP",
            "UNION", "WHERE", "md5", "sha256", "bcrypt", "hashlib", "AES",
            "RSA", "JWT", "token", "cursor", "cipher", "encrypt", "decrypt",
            "N+1", "循环", "loop", "fetchall", "fetchone",
            "参数化", "parameterized", "硬编码", "hardcoded", "SECRET_KEY",
            "API_KEY", "密码", "password", "session", "缓存", "cache",
            "decorator", "装饰器", "logging", "print", "sleep", "hmac",
            "salt", "padding", "PKCS", "injection", "注入",
        ]
        content_lower = content[:1500].lower()
        for term in tech_keywords:
            if term.lower() in content_lower:
                keywords.add(term.lower())

        # 3. 从内容中的反引号代码片段提取标识符
        code_snippets = re.findall(r'`([^`]{3,80})`', content)
        for snippet in code_snippets[:8]:
            identifiers = re.findall(r'\b([a-zA-Z_]\w{2,})\b', snippet)
            keywords.update(i.lower() for i in identifiers)

        signatures[name] = {
            "keywords": list(keywords)[:30],  # 限制每模式最多 30 个关键词
            "title": content.split("\n")[0].replace("# 模式: ", "").strip() if content.startswith("#") else name,
        }

    return signatures


def _get_cached_pattern(pattern_file: Path) -> str:
    """读取模式文件（带 mtime 缓存，减少磁盘 I/O）"""
    mtime = pattern_file.stat().st_mtime
    cached = _pattern_cache.get(pattern_file.name)
    if cached and cached[0] == mtime:
        return cached[1]

    content = pattern_file.read_text(encoding="utf-8")
    _pattern_cache[pattern_file.name] = (mtime, content)
    return content


def recall_knowledge(pr_diff: str) -> str:
    """
    扫描 PR diff，匹配已知模式，返回应注入 Agent 的知识片段
    
    ⚡ 优化：
    1. 动态构建签名表（扫描所有 .md 文件，不再硬编码）
    2. 相关性评分（关键词命中数 + 模式审查次数加权）
    3. Top-K 截断（最多注入 5 个模式）
    4. Token 预算控制（总字符 ≤ 5000）
    5. 文件缓存（避免重复磁盘 I/O）
    
    Returns:
        应追加到 system prompt 的知识文本（空字符串 = 无匹配）
    """
    diff_lower = pr_diff.lower()

    # 动态构建签名表
    signatures = _build_dynamic_signatures()
    if not signatures:
        return ""

    # ── 评分 + 匹配 ──
    scored: list[tuple[int, str, str]] = []  # (score, title, summary)

    for pattern_name, sig in signatures.items():
        pattern_file = PATTERNS_DIR / f"{pattern_name}.md"
        if not pattern_file.exists():
            continue

        # 关键词命中数
        hits = sum(1 for kw in sig["keywords"] if kw in diff_lower)
        if hits < MIN_KEYWORD_MATCHES:
            continue

        # 加权：审查次数多的模式加分
        content = _get_cached_pattern(pattern_file)
        count_match = re.search(r'## 审查次数: (\d+)', content)
        review_count = int(count_match.group(1)) if count_match else 1
        score = hits + min(review_count, 10)  # 审查次数最多加 10 分

        # 摘要：取标准修复 + 一个案例
        fix_match = re.search(r'## 标准修复\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        case_match = re.search(r'### 案例 \d+\n(.+?)(?=\n###|\Z)', content, re.DOTALL)

        summary_parts = [f"**模式**: {sig['title']} (命中 {hits} 关键词, 审查 {review_count} 次)"]
        if fix_match:
            summary_parts.append(f"**标准修复**: {fix_match.group(1).strip()[:300]}")
        if case_match:
            summary_parts.append(f"**最新案例**: {case_match.group(1).strip()[:200]}")

        summary = "\n".join(summary_parts)[:PATTERN_SUMMARY_LENGTH]
        scored.append((score, sig["title"], summary))

    if not scored:
        return ""

    # ── Top-K + Token 预算 ──
    scored.sort(key=lambda x: x[0], reverse=True)
    scored = scored[:MAX_PATTERNS_INJECTED]

    knowledge = "\n\n---\n## 🧠 审查记忆库（历史相似问题）\n\n"
    knowledge += f"> 从 {len(signatures)} 个已知模式中匹配到 {len(scored)} 个相关模式\n"
    knowledge += "> ⚡ 对匹配的模式，如当前代码一致可直接引用已有结论\n\n"

    total_chars = len(knowledge)
    injected = 0
    for score, title, summary in scored:
        chunk = f"### 📚 {title} (相关度: {score}分)\n{summary}\n\n---\n"
        if total_chars + len(chunk) > MAX_MEMORY_CHARS:
            break  # 超出 token 预算，停止注入
        knowledge += chunk
        total_chars += len(chunk)
        injected += 1

    if injected == 0:
        return ""

    return knowledge


# ============================================================
# Phase 2: 审查后 — 归档新知识
# ============================================================

def save_review_to_memory(report: str, pr_diff: str, title: str = ""):
    """
    审查完成后，将发现归档到记忆库
    
    1. 保存完整报告到 memory/reviews/
    2. 从报告中提取问题 → 更新/创建 memory/patterns/ 下的模式文件
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_title = _slugify(title)[:40] if title else "review"

    # ── 1. 保存完整报告 ──
    review_file = REVIEWS_DIR / f"{timestamp}_{safe_title}.md"
    review_file.write_text(report, encoding="utf-8")

    # ── 2. 提取问题并更新模式文件 ──
    _extract_and_update_patterns(report, pr_diff, title, timestamp)

    return review_file


def _extract_and_update_patterns(report: str, pr_diff: str, title: str, timestamp: str):
    """
    从报告中提取 finding，更新对应模式文件
    
    策略：用正则从报告的 "### 🔴/🟠/🟡/🟢/ℹ️ 标题" 格式中提取
    """
    # 匹配报告中的 finding 标题
    finding_pattern = re.compile(
        r'### (🔴|🟠|🟡|🟢|ℹ️) (.+?)\n'
        r'- \*\*文件\*\*: `(.+?)`\n'
        r'- \*\*行号\*\*: (.+?)\n'
        r'- \*\*严重程度\*\*: (.+?)\n'
        r'- \*\*描述\*\*: (.+?)\n'
        r'- \*\*建议\*\*: (.+?)\n',
        re.DOTALL
    )

    findings = []
    for match in finding_pattern.finditer(report):
        findings.append({
            "severity_emoji": match.group(1),
            "title": match.group(2).strip(),
            "file": match.group(3).strip(),
            "lines": match.group(4).strip(),
            "severity": match.group(5).strip(),
            "description": match.group(6).strip().replace("\n", " "),
            "suggestion": match.group(7).strip().replace("\n", " "),
        })

    # 按关键词将 finding 归类到模式文件
    for f in findings:
        pattern_name = _classify_finding(f)
        if not pattern_name:
            continue

        pattern_file = PATTERNS_DIR / f"{pattern_name}.md"

        # ── 创建或更新模式文件 ──
        if pattern_file.exists():
            _update_pattern(pattern_file, f, title, timestamp)
        else:
            _create_pattern(pattern_file, pattern_name, f, title, timestamp)


def _classify_finding(finding: dict) -> Optional[str]:
    """根据 finding 标题和描述，归类到已知模式"""
    text = (finding["title"] + " " + finding["description"]).lower()

    category_map = {
        "sql_injection": ["sql", "注入", "injection"],
        "hardcoded_secret": ["硬编码", "hardcoded", "密钥", "secret", "密码", "password"],
        "md5_hash": ["md5", "哈希", "hash"],
        "n_plus_1_query": ["n+1", "循环", "逐条", "批量", "loop", "batch"],
        "missing_parameterization": ["参数化", "parameterized", "占位符", "placeholder"],
        "connection_leak": ["连接", "connection", "泄漏", "关闭", "close", "leak"],
        "magic_number": ["魔法数字", "magic number", "硬编码数值"],
    }

    for name, keywords in category_map.items():
        if any(kw in text for kw in keywords):
            return name

    # 未匹配 → 用标题创建新模式
    return _slugify(finding["title"])


def _create_pattern(pattern_file: Path, name: str, finding: dict, title: str, timestamp: str):
    """创建新的模式文件"""
    content = f"""# 模式: {finding['title']}

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
{finding['suggestion']}

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: {timestamp}
- **来源 PR**: {title}
- **文件**: {finding['file']}:{finding['lines']}
- **严重程度**: {finding['severity']}
- **描述**: {finding['description']}
- **建议**: {finding['suggestion']}

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
"""
    pattern_file.write_text(content, encoding="utf-8")


def _update_pattern(pattern_file: Path, finding: dict, title: str, timestamp: str):
    """更新已有模式文件：增加案例 + 更新计数"""
    current = pattern_file.read_text(encoding="utf-8")

    # 更新审查次数
    count_match = re.search(r'## 审查次数: (\d+)', current)
    if count_match:
        new_count = int(count_match.group(1)) + 1
        current = current.replace(
            f"## 审查次数: {count_match.group(1)}",
            f"## 审查次数: {new_count}"
        )

    # 追加新案例
    case_num = count_match and int(count_match.group(1)) or 1
    new_case = f"""
### 案例 {case_num + 1}
- **日期**: {timestamp}
- **来源 PR**: {title}
- **文件**: {finding['file']}:{finding['lines']}
- **严重程度**: {finding['severity']}
- **描述**: {finding['description']}
- **建议**: {finding['suggestion']}
"""
    current += new_case
    pattern_file.write_text(current, encoding="utf-8")


# ============================================================
# 工具函数
# ============================================================

def get_memory_stats() -> dict:
    """获取记忆库统计信息"""
    patterns = list(PATTERNS_DIR.glob("*.md"))
    reviews = list(REVIEWS_DIR.glob("*.md"))

    total_cases = 0
    for p in patterns:
        content = p.read_text(encoding="utf-8")
        match = re.search(r'## 审查次数: (\d+)', content)
        if match:
            total_cases += int(match.group(1))

    return {
        "pattern_files": len(patterns),
        "review_files": len(reviews),
        "total_cases": total_cases,
    }
