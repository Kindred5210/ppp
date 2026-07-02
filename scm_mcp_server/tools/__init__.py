"""
Tool 分发入口。
"""
from mcp import types
from scm_mcp_server.tools import readonly as _readonly
from scm_mcp_server.tools import write as _write
from scm_mcp_server.tools import special as _special


def call(name: str, args: dict) -> dict:
    for mod in (_readonly, _write, _special):
        result = mod.call(name, args)
        if result is not None:
            return result
    return {"error": f"Tool not implemented: {name}"}


def list_tool_descriptors() -> list[types.Tool]:
    return (
        _readonly.list_tool_descriptors()
        + _write.list_tool_descriptors()
        + _special.list_tool_descriptors()
    )
