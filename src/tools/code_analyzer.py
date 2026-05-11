"""
代码分析工具 — PR diff 预处理和结构化分析
"""
import re
from typing import List, Tuple


def parse_diff_to_files(diff_text: str) -> List[str]:
    """
    从 git diff 中提取变动的文件列表
    
    Args:
        diff_text: git diff 的完整输出
    
    Returns:
        文件路径列表，如 ["src/auth.py", "src/models.py"]
    """
    files = []
    for line in diff_text.split("\n"):
        if line.startswith("diff --git "):
            parts = line.split(" ")
            if len(parts) >= 4:
                # diff --git a/path/to/file b/path/to/file
                file_path = parts[3][2:]  # 去掉 b/ 前缀
                files.append(file_path)
    return list(set(files))  # 去重


def count_diff_lines(diff_text: str) -> int:
    """
    统计 diff 的变动行数（新增 + 删除）
    用于分级路由判断
    """
    count = 0
    for line in diff_text.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            count += 1
        elif line.startswith("-") and not line.startswith("---"):
            count += 1
    return count


def count_diff_files(diff_text: str) -> int:
    """
    统计 diff 中变动的文件数量

    对于多文件 PR，文件数也是路由判断的重要因素：
    - 1 个文件改 100 行 vs 10 个文件各改 10 行
    - 后者涉及面更广，应该升级审查级别
    """
    files = parse_diff_to_files(diff_text)
    return len(files)


def truncate_diff(diff_text: str, max_lines: int = 500, context_lines: int = 3) -> str:
    """
    截断过大的 diff，减少 Token 消耗

    策略：
    1. 只保留有实际变动（+/-）的行及其上下文
    2. 去掉纯上下文大段（如整个未修改的函数）
    3. 超过 max_lines 时截断中间部分，保留头尾

    面试可讲：不是简单截断，而是"智能保留关键变更 + 局部上下文"
    """
    lines = diff_text.split("\n")
    if len(lines) <= max_lines:
        return diff_text

    result = []
    recent_change = False
    context_counter = 0
    skipped = 0
    kept = 0

    for line in lines:
        is_change = (line.startswith("+") and not line.startswith("+++")) or \
                    (line.startswith("-") and not line.startswith("---"))
        is_header = line.startswith("diff --git") or line.startswith("@@") or \
                    line.startswith("---") or line.startswith("+++")

        if is_change or is_header:
            # 变动行或头部行 → 保留
            if skipped > 0:
                result.append(f"... [省略 {skipped} 行未变更代码] ...")
                skipped = 0
            result.append(line)
            recent_change = True
            context_counter = 0
            kept += 1
        elif recent_change and context_counter < context_lines:
            # 变动行附近保留上下文
            result.append(line)
            context_counter += 1
            kept += 1
        else:
            skipped += 1

    if skipped > 0:
        result.append(f"... [省略 {skipped} 行未变更代码] ...")

    # 如果还是太长，截断中间
    if len(result) > max_lines:
        half = max_lines // 2
        result = result[:half] + [f"\n... [中间省略 {len(result) - max_lines} 行] ...\n"] + result[-half:]

    return "\n".join(result)


def extract_code_snippet(diff_text: str, file_path: str, line_start: int, line_end: int) -> str:
    """
    从 diff 中提取指定行范围的代码片段
    
    Args:
        diff_text: 完整的 diff 内容
        file_path: 目标文件路径
        line_start: 起始行号
        line_end: 结束行号
    
    Returns:
        代码片段字符串
    """
    lines = diff_text.split("\n")
    in_target_file = False
    snippet_lines = []

    for line in lines:
        if f"+++ b/{file_path}" in line or f"+++ b{file_path}" in line:
            in_target_file = True
            continue
        if in_target_file and line.startswith("diff --git"):
            break
        if in_target_file:
            snippet_lines.append(line)

    # 返回相关行
    if line_end > len(snippet_lines):
        line_end = len(snippet_lines)
    if line_start < 1:
        line_start = 1

    return "\n".join(snippet_lines[max(0, line_start - 1):line_end])


def detect_conflicts(findings_by_domain: dict) -> List[dict]:
    """
    冲突检测：找出不同 Agent 之间真正需要权衡的对立观点
    
    两条路径（满足任一条即为冲突）：
    
    路径 1：行号重叠 + 语义对立
      同一段代码被两个 Agent 从不同角度发现问题 → 需要 trade-off
    
    路径 2：修复建议互斥（跨行）
      Security 说"用 bcrypt"，Performance 说"用 SHA256"
      → 即使行号不重叠，建议互相矛盾 → 必须裁决
    
    过滤：
    - 碰巧同行但讨论完全无关的问题（SQL注入 vs 模块耦合）→ 过滤
    - 关键词无交集的正交 finding → 过滤
    """
    all_findings: List[Tuple[str, dict]] = []
    for domain, findings in findings_by_domain.items():
        for f in findings:
            all_findings.append((domain, f))

    conflicts = []
    conflict_id = 0
    seen_pairs = set()  # 防止重复

    for i, (domain_a, fa) in enumerate(all_findings):
        for j, (domain_b, fb) in enumerate(all_findings):
            if j <= i or domain_a == domain_b:
                continue

            pair_key = (min(i, j), max(i, j))
            if pair_key in seen_pairs:
                continue

            # 解析行号
            la_start, la_end = _parse_line_range(fa.get("lines", "0-0"))
            lb_start, lb_end = _parse_line_range(fb.get("lines", "0-0"))

            overlap = max(0, min(la_end, lb_end) - max(la_start, lb_start))
            same_file = fa.get("file") == fb.get("file")
            lines_close = abs(la_start - lb_start) <= 5 if la_start >= 0 and lb_start >= 0 else False

            has_line_conflict = overlap > 0 or (same_file and lines_close)
            has_suggestion_conflict = _check_suggestion_contradiction(fa, fb)

            # ── 两条路径满足任一条 → 候选 ──
            if not (has_line_conflict or has_suggestion_conflict):
                continue

            # ── 语义过滤 ──
            if has_line_conflict and not has_suggestion_conflict:
                # 行号重叠但建议不矛盾 → 检查是否真正有意义
                if not _is_meaningful_conflict(fa, fb, domain_a, domain_b):
                    continue
                conflict_type = "same_line"
            elif has_suggestion_conflict and not has_line_conflict:
                # 建议矛盾但行号不重叠 → 跨行语义冲突
                conflict_type = "cross_line"
            else:
                # 又同行又矛盾 → 最强烈的冲突
                conflict_type = "both"

            seen_pairs.add(pair_key)
            conflict_id += 1

            conflicts.append({
                "conflict_id": f"conflict_{conflict_id}",
                "file": fa.get("file", ""),
                "lines": f"{fa.get('lines','?')}  vs  {fb.get('lines','?')}",
                "conflict_type": conflict_type,
                "code_snippet": fa.get("code_snippet", ""),
                "positions": {
                    domain_a: fa.get("description", ""),
                    domain_b: fb.get("description", ""),
                },
                "status": "pending",
                "debate_rounds": 0,
                "resolution": "",
            })

    return conflicts


def _is_meaningful_conflict(
    fa: dict, fb: dict, domain_a: str, domain_b: str
) -> bool:
    """
    判断两个行号重叠的 finding 是否构成「真正的 engineering trade-off」
    而非碰巧同一行但讨论完全无关的问题。
    
    不需要 LLM — 纯规则判断。
    """

    # 规则 A：修复建议矛盾检查
    # 两个 finding 的 suggestion 是否互斥？
    suggestion_a = (fa.get("suggestion", "") + fa.get("fix", "")).lower()
    suggestion_b = (fb.get("suggestion", "") + fb.get("fix", "")).lower()

    # 矛盾模式：一个说"必须参数化/加密"，另一个说"不需要/移除"
    contradictory_pairs = [
        (["参数化", "prepared", "placeholder"], ["不参数化", "直接拼接", "speed", "慢"]),
        (["加密", "encrypt", "bcrypt", "argon2"], ["明文", "不加密", "plaintext"]),
        (["线程安全", "lock", "mutex", "并发安全"], ["全局", "去掉锁", "单线程"]),
    ]
    for affirm_words, deny_words in contradictory_pairs:
        a_affirms = any(w in suggestion_a for w in affirm_words)
        b_denies = any(w in suggestion_b for w in deny_words)
        if a_affirms and b_denies:
            return True
        # 反过来：B 肯定，A 否定
        b_affirms = any(w in suggestion_b for w in affirm_words)
        a_denies = any(w in suggestion_a for w in deny_words)
        if b_affirms and a_denies:
            return True

    # 规则 B：Security + Performance 同时报 high/critical 且同文件同行
    # → 很可能是 「安全 vs 效率」 的 trade-off
    high_domains = {"security", "performance"}
    if {domain_a, domain_b} == high_domains:
        sev_a = fa.get("severity", "").lower()
        sev_b = fb.get("severity", "").lower()
        if sev_a in ("critical", "high") and sev_b in ("critical", "high"):
            return True

    # 规则 C：Severity 差距 ≥ 2 级 → 一方可能严重误判
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    rank_a = sev_order.get(fa.get("severity", "info").lower(), 4)
    rank_b = sev_order.get(fb.get("severity", "info").lower(), 4)
    if abs(rank_a - rank_b) >= 2:
        return True

    # 规则 D：关键词交集 → 讨论的是相关话题吗？
    # 提取 finding 标题中的关键词
    title_a = set(_extract_keywords(fa.get("title", "")))
    title_b = set(_extract_keywords(fb.get("title", "")))
    if len(title_a) > 0 and len(title_b) > 0:
        overlap_keywords = title_a & title_b
        if len(overlap_keywords) >= 2:
            return True  # 关键词重叠 → 可能相关
        if len(overlap_keywords) == 0:
            return False  # 0 重叠 → 正交问题，过滤

    # 默认：同一行号 + 有至少 1 个共同关键词 → 保留
    return True


def _extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词（中文按字符，英文按单词）"""
    words = set()
    # 英文单词
    for w in re.findall(r'\b([a-zA-Z]{3,})\b', text.lower()):
        words.add(w)
    # 中文双字词
    chinese = re.findall(r'[\u4e00-\u9fff]{2,}', text)
    for c in chinese:
        words.add(c)
    return list(words)


def _check_suggestion_contradiction(fa: dict, fb: dict) -> bool:
    """
    检查两个 finding 的修复建议是否互斥（跨行语义冲突）
    
    不看行号，只看修复建议是否互相矛盾。
    
    例: Security 说"用 bcrypt" vs Performance 说"用 SHA256"
        → 密码哈希维度上互斥 → True
    """
    fix_a = (fa.get("suggestion", "") + " " + fa.get("fix", "")).lower()
    fix_b = (fb.get("suggestion", "") + " " + fb.get("fix", "")).lower()

    exclusive_pairs = [
        (["bcrypt", "argon2", "scrypt"], ["sha256", "sha-256", "md5", "sha1"]),
        (["加密", "encrypt", "aes", "cipher"], ["明文", "plaintext", "不加密"]),
        (["参数化", "parameterized", "placeholder"], ["拼接", "concatenat", "f-string", "sprintf"]),
        (["缓存", "cache", "redis", "lru", "cached"], ["不缓存", "不要缓存", "remove cache"]),
        (["异步", "async", "asyncio", "await"], ["同步", "sync", "阻塞", "blocking"]),
        (["拆分", "abstract", "解耦", "extract"], ["内联", "inline", "合并", "不要拆分"]),
    ]

    for affirm_terms, deny_terms in exclusive_pairs:
        a_affirms = any(t in fix_a for t in affirm_terms)
        b_affirms = any(t in fix_b for t in affirm_terms)
        a_denies = any(t in fix_a for t in deny_terms)
        b_denies = any(t in fix_b for t in deny_terms)

        if a_affirms and b_denies:
            return True
        if b_affirms and a_denies:
            return True

    return False


def _parse_line_range(lines_str: str) -> Tuple[int, int]:
    """解析行号范围 "42-45" → (42, 45)"""
    try:
        parts = lines_str.replace("L", "").split("-")
        start = int(parts[0].strip())
        end = int(parts[-1].strip()) if len(parts) > 1 else start
        return start, end
    except (ValueError, IndexError):
        return -1, -1
