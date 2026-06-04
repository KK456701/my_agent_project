"""
CodeGraph MCP 客户端 — 将 CodeGraph 的 MCP 工具暴露为 LangChain Tool

用法:
    loader = CodeGraphMCPLoader(project_root="d:/work/my-project")
    tools = await loader.load_tools()
    # tools 可以直接传给 LangChain Agent 使用
"""
import asyncio
import json
from pathlib import Path
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import BaseTool


class CodeGraphMCPLoader:
    """
    CodeGraph MCP 工具加载器

    启动 CodeGraph MCP Server → 建立 stdio 连接 → 导出 LangChain Tools
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()

    async def load_tools(self) -> list[BaseTool]:
        """
        连接 CodeGraph MCP Server 并加载所有工具

        Returns:
            LangChain Tool 列表，可直接用于 Agent
        """
        # CodeGraph MCP Server 启动参数
        server_params = StdioServerParameters(
            command="codegraph",
            args=["serve", "--mcp"],
            env=None,
        )

        # 建立 stdio 连接
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport

        # 创建 MCP 会话
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()

        # 转换为 LangChain Tools
        tools = await load_mcp_tools(self._session)
        return tools

    async def close(self):
        """清理连接"""
        await self._exit_stack.aclose()

    # ── 便捷方法：直接调用单个工具 ──

    async def get_callers(self, symbol: str, limit: int = 20) -> dict:
        """查询谁调用了指定符号"""
        return await self._call_tool("codegraph_callers", {
            "symbol": symbol,
            "limit": limit,
        })

    async def get_callees(self, symbol: str, limit: int = 20) -> dict:
        """查询指定符号调用了什么"""
        return await self._call_tool("codegraph_callees", {
            "symbol": symbol,
            "limit": limit,
        })

    async def get_impact(self, symbol: str, depth: int = 2) -> dict:
        """分析变更一个符号的影响范围"""
        return await self._call_tool("codegraph_impact", {
            "symbol": symbol,
            "depth": depth,
        })

    async def explore(self, query: str) -> dict:
        """语义探索：理解代码逻辑"""
        return await self._call_tool("codegraph_explore", {
            "query": query,
        })

    async def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用 MCP 工具并解析结果"""
        if not self._session:
            raise RuntimeError("MCP 会话未初始化，请先调用 load_tools()")

        result = await self._session.call_tool(tool_name, arguments)
        # 解析返回的文本内容
        text = ""
        for content in result.content:
            if hasattr(content, "text"):
                text += content.text

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}


# ============================================================
# 集成到 Impact Agent
# ============================================================

async def build_impact_context_with_codegraph(
    diff_text: str,
    changed_files: list[str],
    project_root: str
) -> str:
    """
    用 CodeGraph MCP 生成影响分析上下文

    替代 code_graph.py 中的 build_impact_context()
    """
    # 提取变更符号（复用 code_graph.py 的 extract_changed_symbols）
    from src.tools.code_graph import extract_changed_symbols
    symbols = extract_changed_symbols(diff_text)

    if not symbols:
        return ""

    loader = CodeGraphMCPLoader(project_root)
    context = "\n\n---\n## 🔗 代码图谱分析（CodeGraph）\n\n"

    try:
        await loader.load_tools()

        # 对每个变更符号做影响分析
        for sym in symbols:
            context += f"### 变更符号: `{sym.name}` ({sym.kind}) — {sym.file}\n\n"

            # 查询调用方
            callers = await loader.get_callers(sym.name)
            if callers:
                context += f"**调用方** ({len(callers)} 处):\n"
                for c in callers[:5]:
                    context += f"- `{c.get('name', '?')}` — {c.get('file', '?')}\n"
                context += "\n"

            # 查询被调用方
            callees = await loader.get_callees(sym.name)
            if callees:
                context += f"**被调用方** ({len(callees)} 处):\n"
                for c in callees[:5]:
                    context += f"- `{c.get('name', '?')}`\n"
                context += "\n"

            # 影响范围
            impact = await loader.get_impact(sym.name, depth=2)
            if impact:
                context += f"**影响半径**: {impact.get('affected_count', '?')} 个符号\n\n"

    finally:
        await loader.close()

    return context
