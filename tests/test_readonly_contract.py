from __future__ import annotations

import re

from tests.conftest import DESIGN


WRITE_PREFIXES = (
    "create_",
    "update_",
    "delete_",
    "move_",
    "load_",
    "push_",
    "reset_",
)


def _section(text: str, start_heading: str, end_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[start:end]


def batch1_readonly_tools() -> list[str]:
    text = DESIGN.read_text(encoding="utf-8")
    batch1 = _section(
        text,
        "### 3.3 Batch 1",
        "### 3.4 Batch 2",
    )
    tools: list[str] = []
    for line in batch1.splitlines():
        match = re.match(r"\| `([^`]+)` \| GET `", line)
        if match:
            tools.append(match.group(1))
    return tools


def test_design_batch1_declares_66_readonly_tools() -> None:
    tools = batch1_readonly_tools()

    assert len(tools) == 66
    assert len(set(tools)) == 66


def test_design_batch1_readonly_scope_excludes_write_tools() -> None:
    tools = batch1_readonly_tools()

    assert all(not tool.startswith(WRITE_PREFIXES) for tool in tools)
