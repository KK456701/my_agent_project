"""
Skills 体系 — 按文件类型动态加载领域知识

类似 Claude Code 的 Skills 机制：
- skills/ 目录下存放各领域的 Markdown 知识文件
- 审查前根据 PR 中涉及的文件类型自动加载相关 Skill
- 技能内容注入到对应 Agent 的 system prompt 中

文件 → Skill 映射规则：
  .py        → python_security / python_performance / python_architecture
  .ts/.tsx   → react_best_practices / typescript_security (可扩展)
  .sql       → sql_best_practices
"""
from pathlib import Path
from typing import Dict, List

SKILLS_ROOT = Path(__file__).parent.parent.parent / "skills"

# 文件扩展名 → 技能文件列表映射
EXTENSION_SKILL_MAP: Dict[str, List[str]] = {
    ".py": [
        "python_security.md",
        "python_performance.md",
        "python_architecture.md",
    ],
    ".ts": ["typescript_best_practices.md"],   # 可扩展
    ".tsx": ["react_security.md", "react_performance.md"],  # 可扩展
    ".js": ["javascript_security.md"],
    ".sql": ["sql_best_practices.md"],
    ".go": ["go_best_practices.md"],
}


def _skill_exists(filename: str) -> bool:
    return (SKILLS_ROOT / filename).exists()


def load_skills_for_files(files: List[str]) -> Dict[str, str]:
    """
    根据文件列表加载相关技能
    
    Args:
        files: 变动的文件路径列表
    
    Returns:
        {领域: 技能内容}  如 {"security": "## SQL 注入\n...", ...}
    
    示例：
        files = ["src/auth.py", "src/models.py"]
        → 加载 python_security.md, python_performance.md, python_architecture.md
    """
    extensions = set()
    for f in files:
        ext = Path(f).suffix.lower()
        if ext:
            extensions.add(ext)

    loaded: Dict[str, str] = {}

    for ext in extensions:
        skill_files = EXTENSION_SKILL_MAP.get(ext, [])
        for skill_file in skill_files:
            if not _skill_exists(skill_file):
                continue

            content = (SKILLS_ROOT / skill_file).read_text(encoding="utf-8")

            # 按文件名确定归属领域
            if "security" in skill_file:
                domain = "security"
            elif "performance" in skill_file:
                domain = "performance"
            elif "architecture" in skill_file or "best_practices" in skill_file:
                domain = "architecture"
            else:
                domain = "general"

            if domain not in loaded:
                loaded[domain] = ""
            loaded[domain] += f"\n\n---\n## 📘 技能: {skill_file.replace('.md', '').replace('_', ' ').title()}\n\n{content}"

    return loaded


def get_skill_prompt_injection(files: List[str]) -> Dict[str, str]:
    """
    获取应注入到各 Agent prompt 中的技能知识
    
    Returns:
        {"security": "...注入内容...", "performance": "...", "architecture": "..."}
    """
    skills = load_skills_for_files(files)

    injections = {}
    for domain, content in skills.items():
        header = f"\n\n---\n## 🎯 团队编码规范（Skills 知识库）\n\n"
        header += "> 以下是团队积累的编码规范，请优先参考这些标准进行审查。\n"
        injections[domain] = header + content

    return injections
