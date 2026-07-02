"""
MCP server 入口：stdio 传输，list_tools 返回空列表（Phase 3 起逐步填充）。
"""
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

import scm_mcp_server.tools as tools
from scm_mcp_server.config import load as load_config

app = Server("scm-mcp-server")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return tools.list_tool_descriptors()


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    result = tools.call(name, arguments)
    import json
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


def main() -> None:
    try:
        load_config()
    except RuntimeError as exc:
        print(f"[scm-mcp-server] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("[scm-mcp-server] Starting (stdio)...", file=sys.stderr)
    import asyncio
    asyncio.run(_run())


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    main()
