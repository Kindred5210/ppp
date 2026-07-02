"""Empty MCP tool registry.

Concrete tool descriptors and routing are intentionally TBD until WORKFLOW.md
Phase 1 fills the tool-to-endpoint mapping from OpenAPI specs.
"""

from __future__ import annotations

from typing import Any

from mcp import types


def list_tool_descriptors() -> list[types.Tool]:
    return []


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"error": f"Tool not implemented: {name}"}
