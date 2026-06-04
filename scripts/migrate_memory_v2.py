"""
记忆文件格式迁移脚本 v1 → v2

旧格式:
  # 模式: XXX
  ## 代码特征 / 标准修复 / 审查次数: N
  ## 历史案例 (含 严重程度 / 建议)

新格式:
  ---
  name: "XXX"
  description: "YYY"
  ---
  ## 历史案例 (含 描述 / 修复，无 严重程度/建议)

用法: python scripts/migrate_memory_v2.py
"""
import re
import yaml
from pathlib import Path

PATTERNS_DIR = Path(__file__).parent.parent / "memory" / "patterns"
BACKUP_DIR = PATTERNS_DIR / "_backup_v1"


def migrate_all():
    """批量迁移所有模式文件"""
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    md_files = list(PATTERNS_DIR.glob("*.md"))
    print(f"找到 {len(md_files)} 个模式文件\n")

    migrated, skipped = 0, 0
    for md_file in sorted(md_files):
        try:
            if _migrate_one(md_file):
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ❌ {md_file.name}: {e}")
            skipped += 1

    print(f"\n✅ 迁移完成: {migrated} 个, 跳过: {skipped} 个")
    print(f"   备份目录: {BACKUP_DIR}")


def _migrate_one(filepath: Path) -> bool:
    """迁移单个文件，返回 True=已迁移, False=跳过"""
    content = filepath.read_text(encoding="utf-8")

    # 已经是新格式？检查是否有 YAML frontmatter
    if content.startswith("---"):
        print(f"  ⏭️ {filepath.name} — 已是新格式，跳过")
        return False

    # 提取标题
    title_match = re.search(r'# 模式:\s*(.+)', content)
    if not title_match:
        print(f"  ⚠️ {filepath.name} — 找不到标题，跳过")
        return False
    title = title_match.group(1).strip()

    # 生成 description：优先用第一个案例的描述
    description = ""
    first_case_desc = re.search(r'### 案例 1\n- \*\*日期\*\*:.*?\n.*?\n.*?\n.*?\n- \*\*描述\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', content, re.DOTALL)
    if first_case_desc:
        description = first_case_desc.group(1).strip().replace("\n", " ")[:200]
    else:
        # 用标准修复当 description
        fix_match = re.search(r'## 标准修复\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if fix_match:
            description = fix_match.group(1).strip().replace("\n", " ")[:200]
        else:
            description = title

    # 提取所有案例（去掉 严重程度，重命名 建议→修复）
    cases_text = ""
    case_pattern = re.compile(
        r'### (案例 \d+)\n'
        r'- \*\*日期\*\*:\s*(.+?)\n'
        r'- \*\*来源 PR\*\*:\s*(.+?)\n'
        r'- \*\*文件\*\*:\s*(.+?)\n'
        r'(?:- \*\*严重程度\*\*:\s*(.+?)\n)?'
        r'- \*\*描述\*\*:\s*(.+?)\n'
        r'- \*\*(?:建议|修复)\*\*:\s*(.+?)(?=\n###|\n---|\Z)',
        re.DOTALL
    )

    cases = []
    for m in case_pattern.finditer(content):
        case_num = m.group(1)
        date = m.group(2).strip()
        pr = m.group(3).strip()
        file_info = m.group(4).strip()
        desc = m.group(6).strip().replace("\n", " ")
        fix = m.group(7).strip().replace("\n", " ")

        cases.append(
            f"### {case_num}\n"
            f"- **日期**: {date}\n"
            f"- **来源 PR**: {pr}\n"
            f"- **文件**: {file_info}\n"
            f"- **描述**: {desc}\n"
            f"- **修复**: {fix}\n"
        )

    if cases:
        cases_text = "\n".join(cases)

    # 构建新格式
    new_content = f"""---
name: "{title}"
description: "{description}"
---

## 历史案例

{cases_text}
"""

    # 备份旧文件
    backup_path = BACKUP_DIR / filepath.name
    filepath.rename(backup_path)

    # 写入新文件
    filepath.write_text(new_content, encoding="utf-8")
    print(f"  ✅ {filepath.name} → name: {title[:50]}...")
    return True


if __name__ == "__main__":
    migrate_all()
