"""
代码分析工具 — PR diff 预处理和结构化分析
"""
import re
from typing import List, Tuple, Optional


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
    检测需要辩论的对抗性冲突。

    简化流程（2 分支）：
      同位置(line overlap) → 看修复是否互斥
      不同位置              → 看是否同一问题（跨行冲突）
    
    核心原则：位置信号前置，修复互斥是主判据。
    灰色地带默认保守（不辩论），宁漏勿滥。
    """
    all_findings = []
    for domain, findings in findings_by_domain.items():
        for f in findings:
            all_findings.append((domain, f))

    adversarial = []
    orthogonal = []
    conflict_id = 0
    seen = set()

    for i, (da, fa) in enumerate(all_findings):
        for j, (db, fb) in enumerate(all_findings):
            if j <= i or da == db:
                continue
            if (min(i, j), max(i, j)) in seen:
                continue
            if fa.get("file") != fb.get("file"):
                continue

            # ── 位置关系 ──
            la_s, la_e = _parse_line_range(fa.get("lines", "0-0"))
            lb_s, lb_e = _parse_line_range(fb.get("lines", "0-0"))
            lap = max(0, min(la_e, lb_e) - max(la_s, lb_s))
            close = abs(la_s - lb_s) <= 5 if la_s >= 0 and lb_s >= 0 else False
            has_line = lap > 0 or close

            # ── 2 分支判定 ──
            if has_line:
                adv = _check_contradiction_v2(fa, fb)
            else:
                # 不同位置 → 同一问题才对抗（跨行冲突），否则跳过
                adv = _check_same_issue(fa, fb) or None
                if adv is False:
                    continue  # 不同位置 + 不同问题 → 跳过

            seen.add((min(i, j), max(i, j)))
            conflict_id += 1

            entry = {
                "conflict_id": f"conflict_{conflict_id}",
                "file": fa.get("file", ""),
                "lines": f"行 {fa.get('lines','?')} vs 行 {fb.get('lines','?')}",
                "positions": {da: fa.get("description", ""), db: fb.get("description", "")},
                "domain_a": da,
                "domain_b": db,
                "adversarial": adv,
                "status": "pending",
                "debate_rounds": 0,
                "resolution": "",
            }

            if adv:
                adversarial.append(entry)
            else:
                orthogonal.append(entry)

    detect_conflicts._last_orthogonal = orthogonal
    return adversarial


detect_conflicts._last_orthogonal = []


def _check_same_issue(fa: dict, fb: dict) -> bool:
    """
    Step 1: 判断两个 finding 是否在说同一问题（描述语义相似度 > 0.85）
    
    利用 Semantic Reranker 的 embedding 模型计算描述文本的余弦相似度。
    模型不可用时返回 False（保守：认为不同问题，走后续规则判断）。
    """
    desc_a = fa.get("description", "")
    desc_b = fb.get("description", "")
    if not desc_a or not desc_b:
        return False
    try:
        from src.tools.semantic_reranker import compute_similarity
        sim = compute_similarity(desc_a[:500], desc_b[:500])
        return sim is not None and sim > 0.85
    except Exception:
        return False


def _check_contradiction_v2(fa: dict, fb: dict) -> bool:
    """
    三层架构判断两个 finding 的修复建议是否互斥：
    
      Layer 1: 硬编码规则（0 Token, < 1ms）
        5 类高置信度互斥对 + 跨词对组合
      Layer 2: NLI 矛盾检测（本地模型, ~50ms）
        StructBERT NLI 模型，双向 contradiction 检测
        规则未命中时兜底，捕获规则覆盖不到的矛盾
    
    Returns:
        True  = 修复建议互斥
        False = 非互斥（包括模型不可用 → 保守默认）
    """
    fix_a = (fa.get("suggestion", "") + " " + fa.get("fix", "")).strip()
    fix_b = (fb.get("suggestion", "") + " " + fb.get("fix", "")).strip()

    if not fix_a or not fix_b:
        return False

    fix_a_lower = fix_a.lower()
    fix_b_lower = fix_b.lower()

    exclusive_pairs = [
        (["bcrypt", "argon2", "scrypt", "pbkdf2"], ["md5", "sha1", "sha256", "sha-256"]),
        (["参数化", "prepared", "placeholder", "bind"], ["拼接", "f-string", "sprintf", "concatenat"]),
        (["加密", "encrypt", "aes", "cipher"], ["明文", "plaintext", "不加密"]),
        (["异步", "async", "asyncio", "await"], ["同步", "sync", "阻塞", "blocking"]),
        (["缓存", "cache"], ["不要缓存", "移除缓存", "不缓存"]),
        (["删除", "移除", "remove", "不要"], ["保留缓存", "添加缓存", "加缓存", "ttl", "过期"]),
    ]

    for affirm_terms, deny_terms in exclusive_pairs:
        a_affirms = any(t in fix_a_lower for t in affirm_terms)
        b_affirms = any(t in fix_b_lower for t in affirm_terms)
        a_denies = any(t in fix_a_lower for t in deny_terms)
        b_denies = any(t in fix_b_lower for t in deny_terms)
        if (a_affirms and b_denies) or (b_affirms and a_denies):
            return True

    # 跨词对组合：删除+缓存 vs 保留/改进+缓存
    delete_words = ["删除", "移除", "remove", "不要", "禁用"]
    keep_words = ["ttl", "过期", "lru", "redis", "保留", "添加", "cachetools"]
    cache_words = ["cache", "缓存", "token_cache", "_cache"]

    a_has_cache = any(w in fix_a_lower for w in cache_words)
    b_has_cache = any(w in fix_b_lower for w in cache_words)

    if a_has_cache and b_has_cache:
        a_del = any(w in fix_a_lower for w in delete_words)
        b_keep = any(w in fix_b_lower for w in keep_words)
        if a_del and b_keep:
            return True
        b_del = any(w in fix_b_lower for w in delete_words)
        a_keep = any(w in fix_a_lower for w in keep_words)
        if b_del and a_keep:
            return True

    # ── NLI 矛盾检测兜底（规则未命中时）──
    try:
        from src.tools.semantic_reranker import check_contradiction
        result = check_contradiction(fix_a[:300], fix_b[:300])
        if result is not None:
            return result
    except Exception:
        pass

    return False


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


def _parse_line_range(lines_str: str) -> Tuple[int, int]:
    """解析行号范围 "42-45" → (42, 45)"""
    try:
        parts = lines_str.replace("L", "").split("-")
        start = int(parts[0].strip())
        end = int(parts[-1].strip()) if len(parts) > 1 else start
        return start, end
    except (ValueError, IndexError):
        return -1, -1
