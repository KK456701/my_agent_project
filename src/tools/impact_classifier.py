"""
变更影响力分级器 — 决定哪些变更需要用 CodeGraph 深挖

策略:
  1. 快速分类 (正则，0 Token，<1ms)
  2. 高风险标记 → CodeGraph 查询调用方数量
  3. 调用方 ≥ 3 → 深挖 (完整源码 + 关系图)
  4. 调用方 < 3 → 轻量 (只注入调用方摘要)
  5. 低风险 → 跳过
"""
import re
import subprocess
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


CG_PATH = r"C:\Users\lenovo\AppData\Local\codegraph\current\bin\codegraph.cmd"


@dataclass
class ChangeImpact:
    """单个变更的影响力评估"""
    symbol: str
    kind: str               # method / function / class / field / comment / ...
    file: str
    risk: str               # "skip" | "light" | "deep"
    reason: str
    caller_count: int = 0
    callers: list = field(default_factory=list)


# ============================================================
# 第 1 层：快速分类（正则，0 Token）
# ============================================================

SKIP_PATTERNS = [
    # 注释
    (r'^\+\s*//', "comment", "注释变更"),
    (r'^\+\s*/\*', "comment", "块注释变更"),
    # 日志
    (r'^\+\s*log\.\w+\(', "log", "日志语句"),
    (r'^\+\s*LOGGER\.\w+\(', "log", "日志语句"),
    (r'^\+\s*logger\.\w+\(', "log", "日志语句"),
    (r'^\+\s*System\.out\.', "log", "控制台输出"),
    (r'^\+\s*print\(', "log", "print 语句"),
    # 纯字符串/字面量
    (r'^\+\s*"[^"]*"\s*[;,]?\s*$', "string", "字符串字面量"),
    (r"^\+\s*'[^']*'\s*[;,]?\s*$", "string", "字符串字面量"),
    # 空白/格式
    (r'^\+\s*$', "whitespace", "空行"),
    # 测试文件
    (r'test[/\\]', "test", "测试文件"),
    (r'Test\.java$', "test", "测试文件"),
    (r'test_', "test", "测试文件"),
]

DEEP_PATTERNS = [
    # Java 公共方法(新增/修改) — 处理 public static/final/abstract ReturnType methodName(
    (r'^\+\s*public\s+(?:static\s+|final\s+|abstract\s+|synchronized\s+|native\s+)*(?:\w+(?:<[^>]*>)?\s+)(\w+)\s*\(', "public_method", "公共方法变更"),
    # Java 删除函数/方法
    (r'^\-\s*(?:public|private|protected)?\s+(?:static\s+|final\s+|abstract\s+)*(?:\w+(?:<[^>]*>)?\s+)?(\w+)\s*\(', "deleted", "方法被删除"),
    # Java 类/接口定义
    (r'^\+\s*(?:public\s+)?(?:class|interface|@interface|enum)\s+(\w+)', "class_def", "类/接口变更"),
    # 异常声明
    (r'^\+\s*throws\s+', "throws", "异常声明变更"),
    # 配置常量/密钥
    (r'^\+\s*(?:static\s+)?(?:final\s+)?\w+\s+(?:SECRET|API_|TOKEN|PASSWORD|TIMEOUT|ENDPOINT|KEY|SALT)', "config", "配置常量"),
    # Python 函数定义
    (r'^\+\s*def\s+(\w+)\s*\(', "function", "Python 函数变更"),
    # Go 函数定义
    (r'^\+\s*func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', "function", "Go 函数变更"),
]


def _get_caller_count(symbol: str, project_root: str) -> int:
    """用 CodeGraph 快速查询调用方数量"""
    try:
        result = subprocess.run(
            [CG_PATH, "callers", symbol, "--json"],
            cwd=project_root,
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return len(data.get("callers", []))
    except Exception:
        pass
    return 0


def _get_callers_detail(symbol: str, project_root: str) -> list:
    """用 CodeGraph 获取调用方详情"""
    try:
        result = subprocess.run(
            [CG_PATH, "callers", symbol, "--json"],
            cwd=project_root,
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("callers", [])
    except Exception:
        pass
    return []


# ============================================================
# 主入口
# ============================================================

def classify_changes(
    diff_text: str,
    project_root: str,
    deep_threshold: int = 3
) -> tuple[list[ChangeImpact], list[ChangeImpact], list[ChangeImpact]]:
    """
    对 diff 中每个变更行分类

    Returns:
        (skip_list, light_list, deep_list)
        - skip: 不需要 CodeGraph
        - light: 需摘要信息
        - deep: 需完整源码 + 关系图
    """
    skip_list = []
    light_list = []
    deep_list = []

    current_file = ""
    lines = diff_text.split("\n")

    for line in lines:
        # 追踪文件
        if line.startswith("diff --git "):
            parts = line.split(" ")
            current_file = parts[3][2:] if len(parts) >= 4 else ""
            continue

        if not current_file:
            continue

        # ── 第 1 层：快速分类 ──

        # 检查跳过模式
        skip = False
        for pattern, kind, reason in SKIP_PATTERNS:
            if re.search(pattern, line):
                skip_list.append(ChangeImpact(
                    symbol="", kind=kind, file=current_file,
                    risk="skip", reason=reason
                ))
                skip = True
                break
        if skip:
            continue

        # 检查深挖模式
        for pattern, kind, reason in DEEP_PATTERNS:
            m = re.search(pattern, line)
            if m:
                symbol = m.group(1) if m.lastindex else ""
                if not symbol:
                    continue

                # ── 第 2 层：CodeGraph 查询调用方数量 ──
                caller_count = _get_caller_count(symbol, project_root)

                if caller_count >= deep_threshold:
                    callers = _get_callers_detail(symbol, project_root)
                    deep_list.append(ChangeImpact(
                        symbol=symbol, kind=kind, file=current_file,
                        risk="deep", reason=f"{reason} + {caller_count} 个调用方",
                        caller_count=caller_count, callers=callers
                    ))
                elif caller_count > 0:
                    light_list.append(ChangeImpact(
                        symbol=symbol, kind=kind, file=current_file,
                        risk="light", reason=f"{reason}, 但仅 {caller_count} 个调用方",
                        caller_count=caller_count
                    ))
                else:
                    light_list.append(ChangeImpact(
                        symbol=symbol, kind=kind, file=current_file,
                        risk="light", reason=f"{reason}, 无调用方",
                        caller_count=0
                    ))
                break

    return skip_list, light_list, deep_list


def build_impact_report(
    skip_list: list,
    light_list: list,
    deep_list: list
) -> str:
    """生成影响力分级报告"""
    report = "\n## 📊 变更影响力分级\n\n"
    report += f"| 级别 | 数量 | 处理方式 |\n"
    report += f"|------|------|----------|\n"
    report += f"| ⏭️ 跳过 | {len(skip_list)} | 无需 CodeGraph |\n"
    report += f"| 🔍 轻量 | {len(light_list)} | 调用方摘要 |\n"
    report += f"| 🔬 深挖 | {len(deep_list)} | 完整源码+关系图 |\n"

    if deep_list:
        report += "\n### 🔬 需深挖的变更\n\n"
        for c in deep_list:
            report += f"- **`{c.symbol}`** ({c.kind}) — {c.file}\n"
            report += f"  → {c.reason}\n"
            if c.callers:
                for caller in c.callers[:5]:
                    report += f"    - {caller['name']} ({caller['filePath']}:{caller['startLine']})\n"

    if light_list:
        report += "\n### 🔍 轻量关注的变更\n\n"
        for c in light_list:
            report += f"- `{c.symbol}` — {c.reason}\n"

    if skip_list:
        report += f"\n### ⏭️ 跳过的变更 ({len(skip_list)} 项)\n"
        report += "注释/日志/格式/测试变更，无跨文件影响\n"

    return report
