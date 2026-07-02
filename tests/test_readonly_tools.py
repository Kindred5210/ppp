from __future__ import annotations

from typing import Any

from scm_mcp_server import tools
from scm_mcp_server.tools import readonly


def test_objects_operations_and_security_register_60_readonly_tools() -> None:
    names = {tool.name for tool in readonly.list_tool_descriptors()}

    assert len(names) == 60
    assert "list_addresses" in names
    assert "get_external_dynamic_list" in names
    assert "list_config_versions" in names
    assert "get_running_config_version" in names
    assert "list_security_rules" in names
    assert "get_wildfire_anti_virus_profile" in names
    assert "list_url_filtering_categories" in names
    assert "get_url_filtering_category" not in names


def test_list_tool_passes_only_supported_query_params(monkeypatch) -> None:
    calls: list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]] = []

    def fake_request(method: str, path: str, *, params: dict | None, json: dict | None):
        calls.append((method, path, params, json))
        return 200, {"data": [{"id": "one"}]}

    monkeypatch.setattr(readonly.rest_client, "request", fake_request)

    result = tools.call(
        "list_addresses",
        {
            "folder": "Shared",
            "offset": 10,
            "limit": 50,
            "ignored": "value",
        },
    )

    assert result == {"data": [{"id": "one"}]}
    assert calls == [
        (
            "GET",
            "/addresses",
            {"folder": "Shared", "offset": 10, "limit": 50},
            None,
        )
    ]


def test_get_tool_formats_path_params(monkeypatch) -> None:
    calls: list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]] = []

    def fake_request(method: str, path: str, *, params: dict | None, json: dict | None):
        calls.append((method, path, params, json))
        return 200, {"id": "12"}

    monkeypatch.setattr(readonly.rest_client, "request", fake_request)

    result = tools.call("get_config_version", {"version": 12})

    assert result == {"id": "12"}
    assert calls == [("GET", "/config-versions/12", None, None)]


def test_non_2xx_response_is_error_payload(monkeypatch) -> None:
    def fake_request(method: str, path: str, *, params: dict | None, json: dict | None):
        return 404, {"message": "not found"}

    monkeypatch.setattr(readonly.rest_client, "request", fake_request)

    result = tools.call("get_address", {"id": "missing"})

    assert result == {
        "error": "SCM API error",
        "status": 404,
        "body": {"message": "not found"},
    }


def test_security_rule_position_is_required() -> None:
    descriptor = {
        tool.name: tool for tool in readonly.list_tool_descriptors()
    }["list_security_rules"]

    assert descriptor.inputSchema["required"] == ["position"]
    assert descriptor.inputSchema["properties"]["position"] == {
        "type": "string",
        "enum": ["pre", "post"],
        "default": "pre",
    }


def test_signature_lists_do_not_accept_name_filter() -> None:
    descriptor = {
        tool.name: tool for tool in readonly.list_tool_descriptors()
    }["list_anti_spyware_signatures"]

    assert "name" not in descriptor.inputSchema["properties"]

