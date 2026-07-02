"""MCP stdio server entrypoint."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from scm_mcp_server.config import load as load_config
from scm_mcp_server import tools

app = Server("scm-mcp-server")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return no business tools until WORKFLOW.md Phase 1 fills descriptors."""
    return tools.list_tool_descriptors()


@app.call_tool()
async def call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
) -> list[types.TextContent]:
    result = tools.call(name, arguments or {})
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


def main() -> None:
    try:
        load_config()
    except RuntimeError as exc:
        print(f"[scm-mcp-server] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("[scm-mcp-server] Starting (stdio)...", file=sys.stderr)
    asyncio.run(_run())


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    main()
