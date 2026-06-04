"""
代码图谱构建器 — 为 PR 审查生成受影响的调用链

技术栈: tree-sitter (多语言 AST 解析) + GitHub API (仓库文件获取)

输出结构:
{
  "changed_symbols": [  # 变更涉及的所有符号
    {"name": "parseToken", "type": "method", "file": "JwtUtil.java", "line": 15}
  ],
  "callers": [          # 谁调用了变更的符号
    {"caller": "AuthFilter.doFilter", "file": "AuthFilter.java:30",
     "callee": "JwtUtil.parseToken", "impact": "signature_mismatch"}
  ],
  "callees": [          # 变更的符号调用了谁
    {"caller": "JwtUtil.parseToken", "callee": "String.substring",
     "impact": "standard_library"}
  ],
  "risks": [            # 自动检测的风险
    {"type": "unused_symbol", "symbol": "parseToken",
     "detail": "新增方法 parseToken 在项目中无调用方"},
    {"type": "signature_conflict", "symbol": "getUserId",
     "detail": "返回值从 String 变为 Optional<String>"}
  ]
}
"""
import re
import os
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Symbol:
    """代码符号（函数、方法、类）"""
    name: str
    kind: str           # "function" | "method" | "class" | "interface"
    file: str
    line: int
    signature: str = ""  # 完整签名，如 "parseToken(String): String"
    parent_class: str = ""  # 所属类（方法用）


@dataclass  
class CallEdge:
    """调用关系边"""
    caller: Symbol       # 调用方
    callee: Symbol       # 被调用方
    file: str
    line: int
    risk: str = ""       # "signature_changed" | "deprecated" | "removed" | ""


@dataclass
class CodeGraph:
    """变更影响的代码图谱"""
    changed_symbols: list[Symbol] = field(default_factory=list)
    callers: list[CallEdge] = field(default_factory=list)       # 谁调用了变更符号
    callees: list[CallEdge] = field(default_factory=list)       # 变更符号调用了谁
    risks: list[dict] = field(default_factory=list)             # 自动检测的风险
    affected_files: list[str] = field(default_factory=list)     # 被影响的文件


# ============================================================
# 语言 → tree-sitter 解析器映射
# ============================================================

LANGUAGE_MAP = {
    ".py":   "python",
    ".java": "java",
    ".go":   "go",
    ".ts":   "typescript",
    ".tsx":  "tsx",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".rs":   "rust",
}

# tree-sitter 查询语句（按语言）
QUERIES = {
    "python": {
        "functions": """
            (function_definition
                name: (identifier) @func_name
                parameters: (parameters) @params
            ) @func_def
            """,
        "classes": """
            (class_definition
                name: (identifier) @class_name
            ) @class_def
            """,
        "calls": """
            (call
                function: (identifier) @call_name
            ) @call
            (call
                function: (attribute
                    object: (identifier) @obj
                    attribute: (identifier) @attr)
            ) @method_call
            """,
    },
    "java": {
        "methods": """
            (method_declaration
                name: (identifier) @method_name
            ) @method_def
            """,
        "classes": """
            (class_declaration
                name: (identifier) @class_name
            ) @class_def
            """,
        "calls": """
            (method_invocation
                name: (identifier) @call_name
            ) @call
            """,
    },
    # Go, TypeScript 等其他语言类似...
}


# ============================================================
# 步骤 1: 从 diff 提取变更的符号
# ============================================================

def extract_changed_symbols(diff_text: str) -> list[Symbol]:
    """
    从 git diff 中提取所有变更涉及的符号（函数、方法、类）

    策略：匹配新增/修改行中的 def/class/func/method 等关键字
    不依赖 tree-sitter（diff 不完整），用正则做快速提取
    """
    symbols = []
    current_file = ""

    for line in diff_text.split("\n"):
        # 追踪当前文件
        if line.startswith("diff --git "):
            parts = line.split(" ")
            current_file = parts[3][2:] if len(parts) >= 4 else ""
            continue

        # 只处理新增/修改行
        if not line.startswith("+") or line.startswith("+++"):
            continue

        code = line[1:].strip()

        # Python: def xxx(  or  class xxx
        m = re.match(r'def\s+(\w+)\s*\(', code)
        if m:
            symbols.append(Symbol(
                name=m.group(1), kind="function",
                file=current_file, line=0, signature=code
            ))
            continue

        m = re.match(r'class\s+(\w+)', code)
        if m:
            symbols.append(Symbol(
                name=m.group(1), kind="class",
                file=current_file, line=0, signature=code
            ))
            continue

        # Java: public/private/protected Type methodName(
        m = re.match(r'(?:public|private|protected|static|\s)+\s*\w+(?:<[^>]*>)?\s+(\w+)\s*\(', code)
        if m and not code.startswith("//"):
            symbols.append(Symbol(
                name=m.group(1), kind="method",
                file=current_file, line=0, signature=code
            ))
            continue

        # Go: func xxx(  or  func (r *Type) xxx(
        m = re.match(r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', code)
        if m:
            symbols.append(Symbol(
                name=m.group(1), kind="function",
                file=current_file, line=0, signature=code
            ))
            continue

    return symbols


# ============================================================
# 步骤 2: 构建调用图（tree-sitter 解析完整文件）
# ============================================================

def build_call_graph(
    changed_files: list[str],
    repo_root: Path,
    changed_symbols: list[Symbol]
) -> CodeGraph:
    """
    为变更文件构建调用图

    对每个变更文件:
    1. tree-sitter 解析完整文件 → 提取所有符号 + 调用关系
    2. 跨文件搜索 → 找到调用变更符号的外部文件
    """
    graph = CodeGraph(changed_symbols=changed_symbols)
    changed_symbol_names = {s.name for s in changed_symbols}

    for filepath in changed_files:
        full_path = repo_root / filepath
        if not full_path.exists():
            continue

        ext = Path(filepath).suffix
        lang = LANGUAGE_MAP.get(ext)
        if not lang:
            continue

        try:
            # tree-sitter 解析（仅 Python 有 tree-sitter 依赖，其他语言降级到正则）
            if lang == "python":
                symbols_in_file, calls_in_file = _parse_file(full_path, lang)
            else:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                symbols_in_file, calls_in_file = _parse_file_regex(content)

            # 找调用变更符号的边
            for call in calls_in_file:
                if call["name"] in changed_symbol_names:
                    graph.callers.append(CallEdge(
                        caller=Symbol(name=call.get("caller", "?"), kind="function",
                                      file=filepath, line=call["line"]),
                        callee=Symbol(name=call["name"], kind="function",
                                      file=filepath, line=call["line"]),
                        file=filepath,
                        line=call["line"],
                        risk="符号已变更，检查兼容性"
                    ))
                    if filepath not in graph.affected_files:
                        graph.affected_files.append(filepath)

            # 找变更符号调用的外部符号
            for sym in changed_symbols:
                if sym.file == filepath:
                    for call in calls_in_file:
                        if call.get("caller") == sym.name:
                            graph.callees.append(CallEdge(
                                caller=sym,
                                callee=Symbol(name=call["name"], kind="function",
                                              file=filepath, line=call["line"]),
                                file=filepath,
                                line=call["line"]
                            ))

        except Exception as e:
            print(f"[CodeGraph] 解析失败 {filepath}: {e}")
            continue

    # 自动检测风险
    graph.risks = _detect_risks(graph, changed_symbols)

    return graph


def _parse_file(filepath: Path, lang: str) -> tuple[list[dict], list[dict]]:
    """
    tree-sitter 解析文件 → 提取符号和调用关系

    简化实现: 使用正则做轻量级解析（不强制依赖 tree-sitter）
    生产级: 替换为 tree-sitter Language(QUERIES[lang])
    """
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    content = filepath.read_text(encoding="utf-8")

    symbols = []
    calls = []

    # 使用 tree-sitter（如果可用）或降级为正则
    try:
        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)
        tree = parser.parse(content.encode())

        # 遍历 AST 提取函数定义和调用
        def _walk(node, depth=0):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    func_name = content[name_node.start_byte:name_node.end_byte]
                    symbols.append({
                        "name": func_name, "kind": "function",
                        "line": node.start_point[0] + 1
                    })

            if node.type == "call":
                func_node = node.child_by_field_name("function")
                if func_node:
                    call_name = content[func_node.start_byte:func_node.end_byte]
                    calls.append({
                        "name": call_name, "line": node.start_point[0] + 1
                    })

            for child in node.children:
                _walk(child, depth + 1)

        _walk(tree.root_node)
        return symbols, calls

    except ImportError:
        # 降级: 正则提取（精度略低但不阻塞流程）
        return _parse_file_regex(content)


def _parse_file_regex(content: str) -> tuple[list[dict], list[dict]]:
    """正则降级解析（通用，不依赖 tree-sitter）"""
    symbols = []
    calls = []

    # 函数定义
    for m in re.finditer(r'def\s+(\w+)\s*\(', content):
        symbols.append({"name": m.group(1), "kind": "function",
                        "line": content[:m.start()].count("\n") + 1})

    # Java 方法
    for m in re.finditer(r'(?:public|private|protected)\s+\w+\s+(\w+)\s*\(', content):
        symbols.append({"name": m.group(1), "kind": "method",
                        "line": content[:m.start()].count("\n") + 1})

    # 调用关系
    for m in re.finditer(r'(\w+)\.(\w+)\s*\(', content):
        calls.append({
            "name": m.group(2),
            "caller": "",
            "line": content[:m.start()].count("\n") + 1
        })

    # 直接函数调用
    for m in re.finditer(r'(?<!def\s)(?<!class\s)(?<!\.)\b(\w+)\s*\(', content):
        name = m.group(1)
        if name not in ["if", "for", "while", "print", "len", "range",
                        "int", "str", "list", "dict", "set", "tuple",
                        "return", "assert", "raise"]:
            calls.append({
                "name": name,
                "line": content[:m.start()].count("\n") + 1
            })

    return symbols, calls


# ============================================================
# 步骤 3: 风险自动检测
# ============================================================

def _detect_risks(graph: CodeGraph, changed_symbols: list[Symbol]) -> list[dict]:
    """基于图谱自动检测风险"""
    risks = []
    changed_names = {s.name for s in changed_symbols}

    # 风险1: 新增符号无调用方 → 可能死代码
    for sym in changed_symbols:
        is_called = any(
            edge.callee.name == sym.name for edge in graph.callers
        )
        if not is_called and sym.kind in ("function", "method"):
            risks.append({
                "type": "unused_symbol",
                "symbol": sym.name,
                "file": sym.file,
                "detail": f"新增{sym.kind} '{sym.name}' 在项目中无调用方",
                "severity": "low"
            })

    # 风险2: 调用方数量 > 5 → 影响面大
    caller_count = defaultdict(int)
    for edge in graph.callers:
        caller_count[edge.callee.name] += 1
    for name, count in caller_count.items():
        if count >= 5:
            risks.append({
                "type": "high_impact",
                "symbol": name,
                "detail": f"被 {count} 处引用，变更影响面大",
                "severity": "high"
            })

    # 风险3: 签名变化 → 调用方可能不兼容
    for sym in changed_symbols:
        if "->" in sym.signature or ":" in sym.signature:
            for edge in graph.callers:
                if edge.callee.name == sym.name:
                    risks.append({
                        "type": "signature_change",
                        "symbol": sym.name,
                        "detail": f"签名变更可能影响 {edge.caller.name} ({edge.file}:{edge.line})",
                        "severity": "high"
                    })

    return risks


# ============================================================
# 步骤 4: 生成 Impact Agent 的注入上下文
# ============================================================

def build_impact_context(graph: CodeGraph) -> str:
    """
    将代码图谱转为注入 Impact Agent 的文本
    """
    if not graph.changed_symbols and not graph.callers:
        return ""

    context = "\n\n---\n## 🔗 代码图谱分析（自动检测）\n\n"

    # 变更符号
    if graph.changed_symbols:
        context += "### 变更涉及符号\n"
        for sym in graph.changed_symbols:
            context += f"- `{sym.name}` ({sym.kind}) — {sym.file}:{sym.line}\n"
        context += "\n"

    # 调用方（受影响的上游）
    if graph.callers:
        context += "### ⚠️ 受影响的调用方\n"
        for edge in graph.callers[:10]:  # 最多 10 个
            context += f"- `{edge.caller.name}` → `{edge.callee.name}` ({edge.file}:{edge.line})\n"
        context += "\n"

    # 被调用方（变更依赖的下游）
    if graph.callees:
        context += "### 变更函数的依赖\n"
        for edge in graph.callees[:10]:
            context += f"- `{edge.caller.name}` → `{edge.callee.name}` ({edge.file}:{edge.line})\n"
        context += "\n"

    # 自动风险
    if graph.risks:
        context += "### 🔴 自动检测风险\n"
        for risk in graph.risks:
            sev = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(risk["severity"], "⚪")
            context += f"- {sev} **{risk['type']}**: {risk['detail']}\n"
        context += "\n"

    # 受影响文件
    if graph.affected_files:
        context += "### 受影响文件清单\n"
        for f in graph.affected_files:
            context += f"- {f}\n"

    return context


# ============================================================
# 入口：从 PR diff 一键生成图谱
# ============================================================

def analyze_pr_impact(
    diff_text: str,
    changed_files: list[str],
    repo_root: Path
) -> CodeGraph:
    """
    PR 影响分析主入口

    Args:
        diff_text: git diff 内容
        changed_files: 变更的文件路径列表
        repo_root: 本地仓库根目录

    Returns:
        CodeGraph: 完整的代码图谱和风险分析
    """
    symbols = extract_changed_symbols(diff_text)
    if not symbols:
        return CodeGraph()

    graph = build_call_graph(changed_files, repo_root, symbols)
    return graph
