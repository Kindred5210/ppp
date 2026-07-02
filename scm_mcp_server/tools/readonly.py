"""Read-only MCP tool routing.

Concrete Batch 1 routes are filled from DESIGN.md. The runtime path is kept
table-driven so each tool only assembles a request and passes through SCM REST
responses.
"""

from __future__ import annotations

from typing import Any

from mcp import types

from scm_mcp_server import rest_client

Route = tuple[str, tuple[str, ...]]

_LIST_TOOLS: dict[str, Route] = {}
_GET_BY_ID_TOOLS: dict[str, Route] = {}

_COMMON_LOCATION_PARAMS: dict[str, dict[str, Any]] = {
    "folder": {"type": "string"},
    "snippet": {"type": "string"},
    "device": {"type": "string"},
}
_PAGING_PARAMS: dict[str, dict[str, Any]] = {
    "offset": {"type": "integer", "default": 0},
    "limit": {"type": "integer", "default": 200},
}
_COMMON_QUERY_PARAMS: dict[str, dict[str, Any]] = {
    "name": {"type": "string"},
    **_COMMON_LOCATION_PARAMS,
    **_PAGING_PARAMS,
}
_PARAM_SCHEMAS: dict[str, dict[str, Any]] = {
    **_COMMON_QUERY_PARAMS,
    "id": {"type": "string"},
    "version": {"type": "integer"},
    "position": {"type": "string", "enum": ["pre", "post"], "default": "pre"},
    "role": {"type": "string"},
    "principal": {"type": "string"},
}
_REQUIRED_PARAMS = {"id", "version", "position"}

_OBJECT_LIST_PARAMS = ("name", "folder", "snippet", "device", "offset", "limit")
_ID_PARAMS = ("id",)

# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists/get
_LIST_TOOLS.update(
    {
        "list_addresses": ("/addresses", _OBJECT_LIST_PARAMS),
        "list_address_groups": ("/address-groups", _OBJECT_LIST_PARAMS),
        "list_services": ("/services", _OBJECT_LIST_PARAMS),
        "list_service_groups": ("/service-groups", _OBJECT_LIST_PARAMS),
        "list_tags": ("/tags", _OBJECT_LIST_PARAMS),
        "list_application_groups": ("/application-groups", _OBJECT_LIST_PARAMS),
        "list_external_dynamic_lists": (
            "/external-dynamic-lists",
            _OBJECT_LIST_PARAMS,
        ),
    }
)

# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses~1{id}/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups~1{id}/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services~1{id}/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups~1{id}/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags~1{id}/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups~1{id}/get
# ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists~1{id}/get
_GET_BY_ID_TOOLS.update(
    {
        "get_address": ("/addresses/{id}", _ID_PARAMS),
        "get_address_group": ("/address-groups/{id}", _ID_PARAMS),
        "get_service": ("/services/{id}", _ID_PARAMS),
        "get_service_group": ("/service-groups/{id}", _ID_PARAMS),
        "get_tag": ("/tags/{id}", _ID_PARAMS),
        "get_application_group": ("/application-groups/{id}", _ID_PARAMS),
        "get_external_dynamic_list": ("/external-dynamic-lists/{id}", _ID_PARAMS),
    }
)

# ref: openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1jobs/get
# ref: openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions/get
_LIST_TOOLS.update(
    {
        "list_jobs": ("/jobs", ()),
        "list_config_versions": ("/config-versions", ("limit", "offset")),
    }
)

# ref: openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1jobs~1{id}/get
# ref: openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions~1{version}/get
# ref: openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions~1running/get
_GET_BY_ID_TOOLS.update(
    {
        "get_job": ("/jobs/{id}", _ID_PARAMS),
        "get_config_version": ("/config-versions/{version}", ("version",)),
        "get_running_config_version": ("/config-versions/running", ()),
    }
)


def list_tool_descriptors() -> list[types.Tool]:
    return [
        _tool_descriptor(name, route)
        for name, route in {**_LIST_TOOLS, **_GET_BY_ID_TOOLS}.items()
    ]


def call(name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    if name in _LIST_TOOLS:
        path, param_keys = _LIST_TOOLS[name]
        return _request(path, param_keys, args)
    if name in _GET_BY_ID_TOOLS:
        path_template, param_keys = _GET_BY_ID_TOOLS[name]
        return _request(path_template, param_keys, args)
    return None


def _tool_descriptor(name: str, route: Route) -> types.Tool:
    _path, param_keys = route
    return types.Tool(
        name=name,
        description=f"Read-only SCM tool: {name}",
        inputSchema=_input_schema(param_keys),
    )


def _input_schema(param_keys: tuple[str, ...]) -> dict[str, Any]:
    properties = {key: _PARAM_SCHEMAS[key] for key in param_keys}
    required = [key for key in param_keys if key in _REQUIRED_PARAMS]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _request(
    path_template: str,
    param_keys: tuple[str, ...],
    args: dict[str, Any],
) -> dict[str, Any]:
    path_param_keys = _path_param_keys(path_template)
    missing = [key for key in path_param_keys if key not in args]
    if missing:
        return {
            "error": "Missing required path parameter",
            "status": 400,
            "body": {"missing": missing},
        }

    path = path_template.format(**{key: args[key] for key in path_param_keys})
    params = {
        key: args[key]
        for key in param_keys
        if key not in path_param_keys and key in args and args[key] is not None
    }
    status, body = rest_client.request(
        "GET",
        path,
        params=params or None,
        json=None,
    )
    if 200 <= status < 300:
        return body
    return {"error": "SCM API error", "status": status, "body": body}


def _path_param_keys(path_template: str) -> tuple[str, ...]:
    keys = []
    parts = path_template.split("{")
    for part in parts[1:]:
        keys.append(part.split("}", 1)[0])
    return tuple(keys)
