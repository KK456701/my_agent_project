"""
代码分析工具 — PR diff 预处理和结构化分析
"""
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
    冲突检测：找出不同 Agent 对同一代码区域的不同判断
    
    简单策略：
    - 同一文件 + 行号范围有重叠 → 可能冲突
    - 进一步检查：如果两个 Agent 的 severity 都是 high/critical → 可能是权衡冲突
    
    Args:
        findings_by_domain: {
            "security": [finding, ...],
            "performance": [finding, ...],
            "architecture": [finding, ...],
        }
    
    Returns:
        冲突列表
    """
    all_findings: List[Tuple[str, dict]] = []
    for domain, findings in findings_by_domain.items():
        for f in findings:
            all_findings.append((domain, f))

    conflicts = []
    conflict_id = 0

    for i, (domain_a, fa) in enumerate(all_findings):
        for j, (domain_b, fb) in enumerate(all_findings):
            if j <= i:
                continue
            if domain_a == domain_b:
                continue

            # 判断行号范围是否有重叠
            la_start, la_end = _parse_line_range(fa.get("lines", "0-0"))
            lb_start, lb_end = _parse_line_range(fb.get("lines", "0-0"))

            if la_start >= 0 and lb_start >= 0:
                overlap = max(0, min(la_end, lb_end) - max(la_start, lb_start))
                if overlap > 0 or (fa.get("file") == fb.get("file") and abs(la_start - lb_start) <= 5):
                    conflict_id += 1
                    conflicts.append({
                        "conflict_id": f"conflict_{conflict_id}",
                        "file": fa.get("file", ""),
                        "lines": f"{min(la_start, lb_start)}-{max(la_end, lb_end)}",
                        "code_snippet": fa.get("code_snippet", ""),
                        "positions": {
                            domain_a: fa.get("description", ""),
                            domain_b: fb.get("description", ""),
                        },
                        "finding_ids": {
                            domain_a: i,
                            domain_b: j,
                        },
                        "status": "pending",
                        "debate_rounds": 0,
                        "resolution": "",
                    })

    return conflicts


def _parse_line_range(lines_str: str) -> Tuple[int, int]:
    """解析行号范围 "42-45" → (42, 45)"""
    try:
        parts = lines_str.replace("L", "").split("-")
        start = int(parts[0].strip())
        end = int(parts[-1].strip()) if len(parts) > 1 else start
        return start, end
    except (ValueError, IndexError):
        return -1, -1
