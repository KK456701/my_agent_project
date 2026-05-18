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
    检测需要辩论的对抗性冲突，正交发现不上报。
    
    新流程（4步递进）：
      Step 1: 同一问题？（描述语义相似度 > 0.85）
      Step 1.5: 同一问题 → 修复互斥？→ 对抗 / 正交
      Step 2: 不同问题 → 修复互斥？（跨行语义冲突）→ 对抗
      Step 3: 行号重叠 → _is_meaningful_conflict_v2 规则判断
      Step 4: 同文件不同行 → _global_semantic_check 兜底
    
    核心原则：修复互斥是主判据，位置/语义是辅助信号。
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

            # 不同文件 → 跳过
            if fa.get("file") != fb.get("file"):
                continue

            # ── 计算位置关系 ──
            la_s, la_e = _parse_line_range(fa.get("lines", "0-0"))
            lb_s, lb_e = _parse_line_range(fb.get("lines", "0-0"))
            lap = max(0, min(la_e, lb_e) - max(la_s, lb_s))
            close = abs(la_s - lb_s) <= 5 if la_s >= 0 and lb_s >= 0 else False
            has_line = lap > 0 or close

            # ── 并行计算三个信号 ──
            is_contra = _check_contradiction_v2(fa, fb)  # True/False/None
            same_issue = _check_same_issue(fa, fb)        # True/False

            # ── 融合判定矩阵 ──
            adv = None  # None = 跳过此对

            if is_contra is True:
                # 修复建议互斥 → 对抗（无论位置/语义）
                adv = True
            elif is_contra is False:
                # 修复建议不互斥
                if same_issue and has_line:
                    adv = False  # 同一问题 + 同一位置 + 修复兼容 → 正交
                else:
                    continue   # 不同问题或无位置重叠 → 跳过
            else:  # is_contra is None（灰色地带）
                if same_issue:
                    if has_line:
                        adv = False  # 同一问题 + 同一位置 → 保守：正交
                    else:
                        adv = True   # 同一问题 + 不同位置 → 跨行冲突
                elif has_line:
                    # 不同问题 + 行号重叠 → 规则兜底
                    adv = _is_meaningful_conflict_v2(fa, fb, da, db)
                    if adv is False:
                        adv = None  # 规则判无关 → 跳过
                else:
                    # 不同问题 + 不同位置 → 全局语义兜底
                    adv = _global_semantic_check(fa, fb)
                    if adv is None:
                        continue

            if adv is None:
                continue

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


def _check_contradiction_v2(fa: dict, fb: dict) -> Optional[bool]:
    """
    规则优先 + 语义兜底：判断两个 finding 的修复建议是否互斥。
    
    Returns:
        True  = 修复建议互斥（矛盾）
        False = 修复建议兼容（方向一致）
        None  = 灰色地带（无法判断）
    
    两层架构（规则先跑！）：
      Layer 1: 硬编码规则（快速、可靠，0 Token）
        捕获 embedding 分不出的同主题矛盾（如"删除缓存"vs"保留缓存+TTL"→0.999）
      Layer 2: Semantic Reranker 兜底（规则未命中时）
        sim > 0.7 → False   sim < 0.3 → True   灰色 → None
    """
    fix_a = (fa.get("suggestion", "") + " " + fa.get("fix", "")).strip()
    fix_b = (fb.get("suggestion", "") + " " + fb.get("fix", "")).strip()

    if not fix_a or not fix_b:
        return None

    fix_a_lower = fix_a.lower()
    fix_b_lower = fix_b.lower()

    # ── Layer 1: 硬编码规则（必须在前，阻止 semantic 误判）──
    # embedding 按主题算相似度，"删除缓存"和"加TTL缓存"都含"缓存"→0.999
    # 规则补这个盲区：规则先命中就返回，不再走 semantic

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

    # 特殊：删除+缓存 vs 保留/改进+缓存（跨词对组合判断）
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

    # ── Layer 2: Semantic Reranker 兜底 ──
    try:
        from src.tools.semantic_reranker import are_suggestions_contradictory
        result = are_suggestions_contradictory(fix_a[:300], fix_b[:300])
        if result is not None:
            return result
    except Exception:
        pass

    return None


def _is_meaningful_conflict_v2(
    fa: dict, fb: dict, domain_a: str, domain_b: str
) -> bool:
    """
    行号重叠 + 不同问题 + 修复灰色地带 → 判断是否构成有意义的冲突。
    
    修复点：
    - 去掉盲判规则（原规则B sec+perf都high直接判对抗）
    - 默认值改为 False（保守，不过度送辩论）
    """

    # 规则 1: severity 差距 ≥ 2 级 → 一方可能严重误判
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    rank_a = sev_order.get(fa.get("severity", "info").lower(), 4)
    rank_b = sev_order.get(fb.get("severity", "info").lower(), 4)
    if abs(rank_a - rank_b) >= 2:
        return True

    # 规则 2: 标题关键词交集
    title_a = set(_extract_keywords(fa.get("title", "")))
    title_b = set(_extract_keywords(fb.get("title", "")))
    overlap = title_a & title_b

    if len(overlap) == 0:
        return False  # 完全无关话题

    # 规则 3: security + performance 都 high/critical + 关键词交集 ≥ 2
    # （加了交集约束，不再盲判）
    if {domain_a, domain_b} == {"security", "performance"}:
        sev_a = fa.get("severity", "").lower()
        sev_b = fb.get("severity", "").lower()
        if sev_a in ("critical", "high") and sev_b in ("critical", "high") and len(overlap) >= 2:
            return True

    # 规则 4: semantic reranker 兜底
    fix_a = fa.get("suggestion", fa.get("fix", ""))
    fix_b = fb.get("suggestion", fb.get("fix", ""))
    if fix_a and fix_b:
        try:
            from src.tools.semantic_reranker import are_suggestions_contradictory
            result = are_suggestions_contradictory(fix_a[:300], fix_b[:300])
            if result is True:
                return True
            if result is False:
                return False
        except Exception:
            pass

    # 默认：保守 → 不送辩论
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


def _global_semantic_check(fa: dict, fb: dict) -> Optional[bool]:
    fix_a = fa.get('suggestion', fa.get('fix', ''))
    fix_b = fb.get('suggestion', fb.get('fix', ''))
    if not fix_a or not fix_b:
        return None
    ta = set(_extract_keywords(fa.get('title', '')))
    tb = set(_extract_keywords(fb.get('title', '')))
    if ta and tb and not (ta & tb):
        return None
    try:
        from src.tools.semantic_reranker import are_suggestions_contradictory
        return are_suggestions_contradictory(fix_a[:300], fix_b[:300])
    except Exception:
        return None


def _parse_line_range(lines_str: str) -> Tuple[int, int]:
    """解析行号范围 "42-45" → (42, 45)"""
    try:
        parts = lines_str.replace("L", "").split("-")
        start = int(parts[0].strip())
        end = int(parts[-1].strip()) if len(parts) > 1 else start
        return start, end
    except (ValueError, IndexError):
        return -1, -1
