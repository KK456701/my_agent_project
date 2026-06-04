"""
Markdown 审查记忆系统 v2 — DeepSeek 驱动的语义召回与积累

工作流:
  审查前 → DeepSeek 语义召回 → 选出相关模式文件 → 加载案例注入 prompt
  审查后 → DeepSeek 语义分类 → 判断 finding 归入已有模式或新建

md 文件格式 (v2):
  ---
  name: "SQL 注入漏洞"
  description: "使用 f-string/字符串拼接构建 SQL 查询，未使用参数化"
  ---
  ## 历史案例
  ### 案例 1
  - **日期**: ...
  - **来源 PR**: ...
  - **文件**: ...
  - **描述**: ...
  - **修复**: ...
"""
import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import config

MEMORY_ROOT = Path(__file__).parent.parent.parent / "memory"
PATTERNS_DIR = MEMORY_ROOT / "patterns"

MAX_PATTERNS_INJECTED = 5
MAX_MEMORY_CHARS = 5000
DIFF_SUMMARY_CHARS = 3000


# ============================================================
# DeepSeek LLM
# ============================================================

def _get_llm(temperature: float = 0) -> ChatOpenAI:
    """获取 DeepSeek LLM（分类任务用 temperature=0）"""
    return ChatOpenAI(
        model=config.MODEL_NAME,
        temperature=temperature,
        api_key=config.API_KEY,
        base_url=config.API_BASE or None,
    )


# ============================================================
# 解析 frontmatter
# ============================================================

def _parse_frontmatter(filepath: Path) -> dict:
    """解析 md 的 YAML frontmatter → {name, description}"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except Exception:
            return {}
    return {}


def _read_full(filepath: Path) -> str:
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception:
        return ""


# ============================================================
# 构建清单
# ============================================================

def _build_checklist() -> Tuple[str, dict]:
    """扫描所有 .md → (清单文本, {filename: {name, description}})"""
    items = []
    metas = {}
    for md_file in sorted(PATTERNS_DIR.glob("*.md")):
        meta = _parse_frontmatter(md_file)
        if meta.get("name"):
            fname = md_file.stem
            metas[fname] = meta
            items.append(f"- [{fname}] {meta['name']}: {meta.get('description', '')}")
    return "\n".join(items), metas


# ============================================================
# Phase 1: 召回
# ============================================================

def recall_knowledge(pr_diff: str) -> str:
    """
    DeepSeek 语义召回 → 选出相关模式 → 加载案例 → 注入 prompt

    Returns:
        追加到 system prompt 的知识文本（空字符串 = 无匹配）
    """
    checklist, metas = _build_checklist()
    if not metas:
        return ""

    diff_summary = pr_diff[:DIFF_SUMMARY_CHARS]

    try:
        llm = _get_llm(temperature=0)
        response = llm.invoke([
            HumanMessage(content=_recall_prompt(checklist, diff_summary))
        ])
        result = response.content.strip()
    except Exception as e:
        print(f"[Memory] 召回失败: {e}")
        return ""

    if result == "NONE" or not result:
        return ""

    selected = re.findall(r'\[(.+?)\]', result)
    selected = [s for s in selected if s in metas][:MAX_PATTERNS_INJECTED]
    if not selected:
        return ""

    # 拼接注入文本
    knowledge = "\n\n---\n## 🧠 审查记忆库（历史相似问题）\n\n"
    knowledge += f"> 从 {len(metas)} 个已知模式中匹配到 {len(selected)} 个相关模式\n"
    knowledge += "> ⚡ 以下为历史相似案例，如当前代码一致可直接引用已有结论\n\n"

    total_chars = len(knowledge)
    for fname in selected:
        meta = metas[fname]
        full = _read_full(PATTERNS_DIR / f"{fname}.md")
        body = re.sub(r'^---\n.*?\n---\n', '', full, flags=re.DOTALL)
        cases_text = body[:800].strip()

        chunk = (
            f"### 📚 {meta['name']}\n"
            f"> {meta.get('description', '')}\n\n"
            f"{cases_text}\n\n---\n"
        )
        if total_chars + len(chunk) > MAX_MEMORY_CHARS:
            break
        knowledge += chunk
        total_chars += len(chunk)

    return knowledge


def _recall_prompt(checklist: str, diff_summary: str) -> str:
    return f"""你是代码审查记忆库的检索器。以下是所有已知问题模式，以及一个 PR 的代码变更。
请选出与本次 PR 最相关的模式（最多 {MAX_PATTERNS_INJECTED} 个），只输出 ID，每行一个，格式如 [filename]。

已知模式：
{checklist}

PR 代码变更：
```
{diff_summary}
```

只输出相关模式的 ID，每行一个。没有相关模式则只输出 NONE。"""


# ============================================================
# Phase 2: 积累
# ============================================================

def save_review_to_memory(report: str, pr_diff: str = "", title: str = ""):
    """
    DeepSeek 语义积累：对每个 finding 判断归属 → 追加或新建
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    findings = _extract_findings_from_report(report)
    if not findings:
        return

    checklist, metas = _build_checklist()
    llm = _get_llm(temperature=0)

    for finding in findings:
        try:
            _classify_and_update(finding, checklist, metas, llm, title, timestamp)
        except Exception as e:
            print(f"[Memory] 积累失败 ({finding.get('title', '?')[:30]}): {e}")


def _classify_and_update(
    finding: dict, checklist: str, metas: dict,
    llm: ChatOpenAI, pr_title: str, timestamp: str
):
    """对单个 finding: DeepSeek 分类 → 追加或新建"""
    prompt = f"""你是代码审查记忆库的分类器。判断以下审查发现应归入哪个已有模式，还是新建模式。

已有模式：
{checklist if checklist else "（暂无已有模式）"}

新发现：
- 标题: {finding.get('title', '')}
- 描述: {finding.get('description', '')}
- 修复: {finding.get('fix', '')}

只输出以下之一（不要输出其他内容）：
- 归入已有模式输出 ID，如 [sql_injection]
- 新建模式输出 NEW"""

    response = llm.invoke([HumanMessage(content=prompt)])
    result = response.content.strip()

    if result == "NEW":
        _create_new_pattern(finding, pr_title, timestamp)
    else:
        match = re.search(r'\[(.+?)\]', result)
        if match and (PATTERNS_DIR / f"{match.group(1)}.md").exists():
            _append_case(PATTERNS_DIR / f"{match.group(1)}.md", finding, pr_title, timestamp)
        else:
            _create_new_pattern(finding, pr_title, timestamp)


def _append_case(filepath: Path, finding: dict, pr_title: str, timestamp: str):
    """追加案例到已有文件"""
    date_str = timestamp.replace('_', ' ')[:16]

    # 去重
    existing = _read_full(filepath)
    file_key = f"{finding.get('file', '')}:{finding.get('lines', '')}"
    if file_key in existing and file_key != ":":
        return

    case_nums = re.findall(r'### 案例 (\d+)', existing)
    case_num = max(int(n) for n in case_nums) + 1 if case_nums else 1

    new_case = f"""
### 案例 {case_num}
- **日期**: {date_str}
- **来源 PR**: {pr_title}
- **文件**: {finding.get('file', '')}:{finding.get('lines', '')}
- **描述**: {finding.get('description', '')}
- **修复**: {finding.get('fix', '')}
"""
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(new_case)


def _create_new_pattern(finding: dict, pr_title: str, timestamp: str):
    """新建记忆模式文件"""
    date_str = timestamp.replace('_', ' ')[:16]
    slug = re.sub(r'[^\w\u4e00-\u9fff_-]', '_', finding.get('title', 'unknown'))[:60]
    slug = re.sub(r'_+', '_', slug).strip('_')
    filepath = PATTERNS_DIR / f"{slug}.md"
    if filepath.exists():
        filepath = PATTERNS_DIR / f"{slug}_{timestamp[-6:]}.md"

    name_safe = finding.get('title', 'Unknown').replace('"', "'")
    desc_safe = (finding.get('description', '') or finding.get('title', ''))[:200].replace('"', "'")

    content = f"""---
name: "{name_safe}"
description: "{desc_safe}"
---

## 历史案例

### 案例 1
- **日期**: {date_str}
- **来源 PR**: {pr_title}
- **文件**: {finding.get('file', '')}:{finding.get('lines', '')}
- **描述**: {finding.get('description', '')}
- **修复**: {finding.get('fix', '')}
"""
    filepath.write_text(content, encoding="utf-8")


# ============================================================
# 从报告提取 finding
# ============================================================

def _extract_findings_from_report(report: str) -> list[dict]:
    """正则提取报告中的所有 finding"""
    findings = []
    skip_keywords = ["静态分析", "辩论裁决", "交叉发现", "总览", "📊"]

    sections = re.split(r'\n## (?=🔴|🟠|🟡|🟢|ℹ️)', report)

    for section in sections:
        if any(s in section for s in skip_keywords):
            continue

        blocks = re.split(r'\n(?=### )', section)
        for block in blocks:
            if not block.strip().startswith('###'):
                continue

            title_match = re.match(r'### (.+?)\n', block)
            if not title_match:
                continue
            title = title_match.group(1).strip()

            if 'Skills 规则命中' in block and '描述' not in block:
                continue

            pos_match = re.search(r'\*\*位置\*\*:\s*`?(.+?)`?(?:\s*\||\n)', block)
            desc_match = re.search(r'\*\*描述\*\*:\s*(.+?)(?=\n- \*\*|\n\n|\n###|\Z)', block, re.DOTALL)
            fix_match = re.search(r'\*\*修复\*\*:\s*(.+?)(?=\n- \*\*|\n\n|\n###|\Z)', block, re.DOTALL)

            description = desc_match.group(1).strip().replace("\n", " ") if desc_match else ""
            fix = fix_match.group(1).strip().replace("\n", " ") if fix_match else ""

            if not description and not fix:
                continue

            file_info = pos_match.group(1).strip() if pos_match else ""
            findings.append({
                "title": title,
                "file": file_info.split(":")[0] if ":" in file_info else file_info,
                "lines": file_info.split(":")[1] if ":" in file_info else "",
                "description": description[:500],
                "fix": fix[:500],
            })

    return findings


# ============================================================
# 统计
# ============================================================

def get_memory_stats() -> dict:
    patterns = list(PATTERNS_DIR.glob("*.md"))
    total_cases = 0
    for p in patterns:
        total_cases += len(re.findall(r'### 案例 \d+', _read_full(p)))
    return {"pattern_files": len(patterns), "total_cases": total_cases}
