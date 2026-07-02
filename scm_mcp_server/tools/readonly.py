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
_LOCATION_PAGING_PARAMS = ("folder", "snippet", "device", "offset", "limit")
_SECURITY_RULE_LIST_PARAMS = (
    "name",
    "position",
    "folder",
    "snippet",
    "device",
    "offset",
    "limit",
)
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

# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules/get
_LIST_TOOLS.update(
    {
        "list_security_rules": ("/security-rules", _SECURITY_RULE_LIST_PARAMS),
        "list_decryption_rules": ("/decryption-rules", _SECURITY_RULE_LIST_PARAMS),
        "list_app_override_rules": (
            "/app-override-rules",
            _SECURITY_RULE_LIST_PARAMS,
        ),
        "list_dos_protection_rules": (
            "/dos-protection-rules",
            _OBJECT_LIST_PARAMS,
        ),
    }
)

# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules~1{id}/get
_GET_BY_ID_TOOLS.update(
    {
        "get_security_rule": ("/security-rules/{id}", _ID_PARAMS),
        "get_decryption_rule": ("/decryption-rules/{id}", _ID_PARAMS),
        "get_app_override_rule": ("/app-override-rules/{id}", _ID_PARAMS),
        "get_dos_protection_rule": ("/dos-protection-rules/{id}", _ID_PARAMS),
    }
)

# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-filtering-categories/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles/get
_LIST_TOOLS.update(
    {
        "list_anti_spyware_profiles": (
            "/anti-spyware-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_anti_spyware_signatures": (
            "/anti-spyware-signatures",
            _LOCATION_PAGING_PARAMS,
        ),
        "list_data_filtering_profiles": (
            "/data-filtering-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_data_objects": ("/data-objects", _OBJECT_LIST_PARAMS),
        "list_decryption_exclusions": (
            "/decryption-exclusions",
            _OBJECT_LIST_PARAMS,
        ),
        "list_decryption_profiles": ("/decryption-profiles", _OBJECT_LIST_PARAMS),
        "list_dns_security_profiles": (
            "/dns-security-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_dos_protection_profiles": (
            "/dos-protection-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_file_blocking_profiles": (
            "/file-blocking-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_http_header_profiles": (
            "/http-header-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_profile_groups": ("/profile-groups", _OBJECT_LIST_PARAMS),
        "list_url_access_profiles": ("/url-access-profiles", _OBJECT_LIST_PARAMS),
        "list_url_categories": ("/url-categories", _OBJECT_LIST_PARAMS),
        "list_url_filtering_categories": (
            "/url-filtering-categories",
            _OBJECT_LIST_PARAMS,
        ),
        "list_vulnerability_protection_profiles": (
            "/vulnerability-protection-profiles",
            _OBJECT_LIST_PARAMS,
        ),
        "list_vulnerability_protection_signatures": (
            "/vulnerability-protection-signatures",
            _LOCATION_PAGING_PARAMS,
        ),
        "list_wildfire_anti_virus_profiles": (
            "/wildfire-anti-virus-profiles",
            _OBJECT_LIST_PARAMS,
        ),
    }
)

# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures~1{id}/get
# ref: openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles~1{id}/get
_GET_BY_ID_TOOLS.update(
    {
        "get_anti_spyware_profile": ("/anti-spyware-profiles/{id}", _ID_PARAMS),
        "get_anti_spyware_signature": (
            "/anti-spyware-signatures/{id}",
            _ID_PARAMS,
        ),
        "get_data_filtering_profile": (
            "/data-filtering-profiles/{id}",
            _ID_PARAMS,
        ),
        "get_data_object": ("/data-objects/{id}", _ID_PARAMS),
        "get_decryption_exclusion": ("/decryption-exclusions/{id}", _ID_PARAMS),
        "get_decryption_profile": ("/decryption-profiles/{id}", _ID_PARAMS),
        "get_dns_security_profile": ("/dns-security-profiles/{id}", _ID_PARAMS),
        "get_dos_protection_profile": (
            "/dos-protection-profiles/{id}",
            _ID_PARAMS,
        ),
        "get_file_blocking_profile": ("/file-blocking-profiles/{id}", _ID_PARAMS),
        "get_http_header_profile": ("/http-header-profiles/{id}", _ID_PARAMS),
        "get_profile_group": ("/profile-groups/{id}", _ID_PARAMS),
        "get_url_access_profile": ("/url-access-profiles/{id}", _ID_PARAMS),
        "get_url_category": ("/url-categories/{id}", _ID_PARAMS),
        "get_vulnerability_protection_profile": (
            "/vulnerability-protection-profiles/{id}",
            _ID_PARAMS,
        ),
        "get_vulnerability_protection_signature": (
            "/vulnerability-protection-signatures/{id}",
            _ID_PARAMS,
        ),
        "get_wildfire_anti_virus_profile": (
            "/wildfire-anti-virus-profiles/{id}",
            _ID_PARAMS,
        ),
    }
)

# ref: openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts/get
# ref: openapi-specs/scm/iam/Roles.yaml#/paths/~1iam~1v1~1roles/get
# ref: openapi-specs/scm/iam/AccessPolicies.yaml#/paths/~1iam~1v1~1access_policies/get
_LIST_TOOLS.update(
    {
        "list_service_accounts": ("/iam/v1/service_accounts", ()),
        "list_roles": ("/iam/v1/roles", ()),
        "list_access_policies": (
            "/iam/v1/access_policies",
            ("role", "principal"),
        ),
    }
)

# ref: openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts~1{id}/get
# ref: openapi-specs/scm/iam/Roles.yaml#/paths/~1iam~1v1~1roles~1{name}/get
# ref: openapi-specs/scm/iam/AccessPolicies.yaml#/paths/~1iam~1v1~1access_policies~1{id}/get
_GET_BY_ID_TOOLS.update(
    {
        "get_service_account": ("/iam/v1/service_accounts/{id}", _ID_PARAMS),
        "get_role": ("/iam/v1/roles/{name}", ("name",)),
        "get_access_policy": ("/iam/v1/access_policies/{id}", _ID_PARAMS),
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
    path, param_keys = route
    return types.Tool(
        name=name,
        description=f"Read-only SCM tool: {name}",
        inputSchema=_input_schema(path, param_keys),
    )


def _input_schema(path_template: str, param_keys: tuple[str, ...]) -> dict[str, Any]:
    properties = {key: _PARAM_SCHEMAS[key] for key in param_keys}
    path_param_keys = set(_path_param_keys(path_template))
    required = [
        key for key in param_keys if key in _REQUIRED_PARAMS or key in path_param_keys
    ]
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
