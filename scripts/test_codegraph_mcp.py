"""
直接调用 CodeGraph MCP 工具 (不依赖任何 MCP SDK)

用 subprocess 启动 codegraph serve --mcp，通过 stdin/stdout 发送 JSON-RPC 请求
"""
import subprocess
import json
import sys

CG_PATH = r"C:\Users\lenovo\AppData\Local\codegraph\current\bin\codegraph.cmd"
PROJECT = r"d:\work\testagentPR"


def rpc_call(process, method: str, params: dict = None) -> dict:
    """发送 JSON-RPC 请求，返回结果"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    payload = json.dumps(request) + "\n"
    process.stdin.write(payload)
    process.stdin.flush()
    
    response_line = process.stdout.readline()
    if response_line:
        return json.loads(response_line)
    return {"error": "no response"}


def main():
    # 启动 CodeGraph MCP Server
    print("启动 CodeGraph MCP Server...")
    proc = subprocess.Popen(
        [CG_PATH, "serve", "--mcp"],
        cwd=PROJECT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    # 1. 初始化 MCP 会话
    print("\n" + "=" * 60)
    print("步骤 1: 初始化 MCP 会话")
    print("=" * 60)
    
    init_resp = rpc_call(proc, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    })
    print(json.dumps(init_resp, indent=2, ensure_ascii=False)[:1000])

    # 通知服务器初始化完成
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    proc.stdin.flush()
    proc.stdout.readline()  # 等待确认

    # 2. 列出可用工具
    print("\n" + "=" * 60)
    print("步骤 2: 列出可用 MCP 工具")
    print("=" * 60)
    
    tools_resp = rpc_call(proc, "tools/list", {})
    print(json.dumps(tools_resp, indent=2, ensure_ascii=False)[:2000])

    # 3. 调用 codegraph_node — 获取 parseToken 完整源码
    print("\n" + "=" * 60)
    print("步骤 3: codegraph_node('parseToken') — 完整源码")
    print("=" * 60)
    
    node_resp = rpc_call(proc, "tools/call", {
        "name": "codegraph_node",
        "arguments": {"symbol": "parseToken"}
    })
    print(json.dumps(node_resp, indent=2, ensure_ascii=False))

    # 4. 调用 codegraph_explore — 探索 parseToken 的完整上下文
    print("\n" + "=" * 60)
    print("步骤 4: codegraph_explore('parseToken 调用链') — 源码+关系")
    print("=" * 60)
    
    explore_resp = rpc_call(proc, "tools/call", {
        "name": "codegraph_explore",
        "arguments": {"query": "parseToken how is it called and what does it do"}
    })
    print(json.dumps(explore_resp, indent=2, ensure_ascii=False))

    proc.terminate()


if __name__ == "__main__":
    main()
