"""
Batch 1 只读 tool 实现。

所有 tool 通过两张路由表驱动，无 if/elif 分支：
  _LIST_TOOLS      — list_*：(path, params_schema)
  _GET_BY_ID_TOOLS — get_*：(path_template, id_key, base_override_or_None)

inputSchema 共享常量来自对应 YAML 的 components/parameters：
  - objects-june.yaml
  - security-services-R2-2026.yaml
  - config-operations-march.yaml
  - ServiceAccounts.yaml / Roles.yaml / AccessPolicies.yaml
"""

from mcp import types
from scm_mcp_server import rest_client

# ---------------------------------------------------------------------------
# Shared inputSchema parameter sets
# ref: objects-june.yaml#/components/parameters
#      security-services-R2-2026.yaml#/components/parameters
# ---------------------------------------------------------------------------

# ref: objects-june.yaml#/components/parameters — folder/snippet/device/name/offset/limit
_CONTAINER_LIST_PARAMS: dict = {
    "type": "object",
    "properties": {
        "folder":  {"type": "string",  "description": "Container: folder name"},
        "snippet": {"type": "string",  "description": "Container: snippet name"},
        "device":  {"type": "string",  "description": "Container: device name"},
        "name":    {"type": "string",  "description": "Filter by object name"},
        "offset":  {"type": "integer", "description": "Pagination offset (default 0)"},
        "limit":   {"type": "integer", "description": "Page size (default 200)"},
    },
    "required": [],
}

# ref: security-services-R2-2026.yaml#/components/parameters — adds position (optional)
_RULES_LIST_PARAMS: dict = {
    "type": "object",
    "properties": {
        **_CONTAINER_LIST_PARAMS["properties"],
        "position": {"type": "string", "description": "Rule position: pre or post"},
    },
    "required": [],
}

# ref: config-operations-march.yaml#/components/parameters — offset/limit only
_OPS_LIST_PARAMS: dict = {
    "type": "object",
    "properties": {
        "offset": {"type": "integer", "description": "Pagination offset"},
        "limit":  {"type": "integer", "description": "Page size"},
    },
    "required": [],
}

# ref: AccessPolicies.yaml — inline query params: role, principal
_IAM_POLICIES_LIST_PARAMS: dict = {
    "type": "object",
    "properties": {
        "role":      {"type": "string", "description": "Filter by role name"},
        "principal": {"type": "string", "description": "Filter by principal"},
    },
    "required": [],
}

# No query params (e.g. list_jobs, get_running_config_version, list_roles, list_service_accounts)
_NO_PARAMS: dict = {
    "type": "object",
    "properties": {},
    "required": [],
}

# get-by-id shared schema
_GET_BY_ID_SCHEMA: dict = {
    "type": "object",
    "properties": {"id": {"type": "string", "description": "Object UUID"}},
    "required": ["id"],
}

_GET_BY_VERSION_SCHEMA: dict = {
    "type": "object",
    "properties": {"version": {"type": "string", "description": "Config version number"}},
    "required": ["version"],
}

_GET_BY_NAME_SCHEMA: dict = {
    "type": "object",
    "properties": {"name": {"type": "string", "description": "Resource name"}},
    "required": ["name"],
}

# ---------------------------------------------------------------------------
# Base URLs
# ---------------------------------------------------------------------------

_OBJECTS_BASE   = "/config/objects/v1"
_SECURITY_BASE  = "/config/security/v1"
_OPS_BASE       = "/config/operations/v1"
_IAM_SASE_BASE  = "https://api.sase.paloaltonetworks.com"

# ---------------------------------------------------------------------------
# _LIST_TOOLS: tool_name → (path, params_schema)
#   path is appended to cfg["base_url"] (or IAM base via caller override)
# ---------------------------------------------------------------------------

_LIST_TOOLS: dict[str, tuple[str, dict]] = {
    # === A1 Objects core — ref: objects-june.yaml ===
    "list_addresses":              (_OBJECTS_BASE + "/addresses",              _CONTAINER_LIST_PARAMS),
    "list_address_groups":         (_OBJECTS_BASE + "/address-groups",         _CONTAINER_LIST_PARAMS),
    "list_services":               (_OBJECTS_BASE + "/services",               _CONTAINER_LIST_PARAMS),
    "list_service_groups":         (_OBJECTS_BASE + "/service-groups",         _CONTAINER_LIST_PARAMS),
    "list_tags":                   (_OBJECTS_BASE + "/tags",                   _CONTAINER_LIST_PARAMS),
    "list_application_groups":     (_OBJECTS_BASE + "/application-groups",     _CONTAINER_LIST_PARAMS),
    "list_external_dynamic_lists": (_OBJECTS_BASE + "/external-dynamic-lists", _CONTAINER_LIST_PARAMS),

    # === B1 Security rules — ref: security-services-R2-2026.yaml ===
    "list_security_rules":         (_SECURITY_BASE + "/security-rules",        _RULES_LIST_PARAMS),
    "list_decryption_rules":       (_SECURITY_BASE + "/decryption-rules",      _RULES_LIST_PARAMS),
    "list_app_override_rules":     (_SECURITY_BASE + "/app-override-rules",    _RULES_LIST_PARAMS),
    "list_dos_protection_rules":   (_SECURITY_BASE + "/dos-protection-rules",  _CONTAINER_LIST_PARAMS),

    # === B2 Security profiles readonly — ref: security-services-R2-2026.yaml ===
    "list_anti_spyware_profiles":              (_SECURITY_BASE + "/anti-spyware-profiles",              _CONTAINER_LIST_PARAMS),
    "list_anti_spyware_signatures":            (_SECURITY_BASE + "/anti-spyware-signatures",            _CONTAINER_LIST_PARAMS),
    "list_data_filtering_profiles":            (_SECURITY_BASE + "/data-filtering-profiles",            _CONTAINER_LIST_PARAMS),
    "list_data_objects":                       (_SECURITY_BASE + "/data-objects",                       _CONTAINER_LIST_PARAMS),
    "list_decryption_exclusions":              (_SECURITY_BASE + "/decryption-exclusions",              _CONTAINER_LIST_PARAMS),
    "list_decryption_profiles":                (_SECURITY_BASE + "/decryption-profiles",                _CONTAINER_LIST_PARAMS),
    "list_dns_security_profiles":              (_SECURITY_BASE + "/dns-security-profiles",              _CONTAINER_LIST_PARAMS),
    "list_dos_protection_profiles":            (_SECURITY_BASE + "/dos-protection-profiles",            _CONTAINER_LIST_PARAMS),
    "list_file_blocking_profiles":             (_SECURITY_BASE + "/file-blocking-profiles",             _CONTAINER_LIST_PARAMS),
    "list_http_header_profiles":               (_SECURITY_BASE + "/http-header-profiles",               _CONTAINER_LIST_PARAMS),
    "list_profile_groups":                     (_SECURITY_BASE + "/profile-groups",                     _CONTAINER_LIST_PARAMS),
    "list_url_access_profiles":                (_SECURITY_BASE + "/url-access-profiles",                _CONTAINER_LIST_PARAMS),
    "list_url_categories":                     (_SECURITY_BASE + "/url-categories",                     _CONTAINER_LIST_PARAMS),
    "list_url_filtering_categories":           (_SECURITY_BASE + "/url-filtering-categories",           _CONTAINER_LIST_PARAMS),
    "list_vulnerability_protection_profiles":  (_SECURITY_BASE + "/vulnerability-protection-profiles",  _CONTAINER_LIST_PARAMS),
    "list_vulnerability_protection_signatures":(_SECURITY_BASE + "/vulnerability-protection-signatures",_CONTAINER_LIST_PARAMS),
    "list_wildfire_anti_virus_profiles":       (_SECURITY_BASE + "/wildfire-anti-virus-profiles",       _CONTAINER_LIST_PARAMS),

    # === C1 Operations — ref: config-operations-march.yaml ===
    "list_jobs":                   (_OPS_BASE + "/jobs",             _NO_PARAMS),
    "list_config_versions":        (_OPS_BASE + "/config-versions",  _OPS_LIST_PARAMS),
    "get_running_config_version":  (_OPS_BASE + "/config-versions/running", _NO_PARAMS),

    # === D1 IAM — ref: ServiceAccounts.yaml / Roles.yaml / AccessPolicies.yaml ===
    # base override handled in call() via _IAM_LIST_BASES
    "list_service_accounts":  ("/iam/v1/service_accounts", _NO_PARAMS),
    "list_roles":              ("/iam/v1/roles",             _NO_PARAMS),
    "list_access_policies":    ("/iam/v1/access_policies",  _IAM_POLICIES_LIST_PARAMS),
}

# Tools that need IAM base override (api.sase.paloaltonetworks.com)
_IAM_TOOL_NAMES: frozenset[str] = frozenset({
    "list_service_accounts", "list_roles", "list_access_policies",
    "get_service_account", "get_role", "get_access_policy",
})

# ---------------------------------------------------------------------------
# _GET_BY_ID_TOOLS: tool_name → (path_template, id_key, inputSchema)
#   path_template uses {id} or {name} or {version} as placeholder
# ---------------------------------------------------------------------------

_GET_BY_ID_TOOLS: dict[str, tuple[str, str, dict]] = {
    # === A1 Objects core ===
    "get_address":              (_OBJECTS_BASE + "/addresses/{id}",              "id",      _GET_BY_ID_SCHEMA),
    "get_address_group":        (_OBJECTS_BASE + "/address-groups/{id}",         "id",      _GET_BY_ID_SCHEMA),
    "get_service":              (_OBJECTS_BASE + "/services/{id}",               "id",      _GET_BY_ID_SCHEMA),
    "get_service_group":        (_OBJECTS_BASE + "/service-groups/{id}",         "id",      _GET_BY_ID_SCHEMA),
    "get_tag":                  (_OBJECTS_BASE + "/tags/{id}",                   "id",      _GET_BY_ID_SCHEMA),
    "get_application_group":    (_OBJECTS_BASE + "/application-groups/{id}",     "id",      _GET_BY_ID_SCHEMA),
    "get_external_dynamic_list":(_OBJECTS_BASE + "/external-dynamic-lists/{id}", "id",      _GET_BY_ID_SCHEMA),

    # === B1 Security rules ===
    "get_security_rule":        (_SECURITY_BASE + "/security-rules/{id}",        "id",      _GET_BY_ID_SCHEMA),
    "get_decryption_rule":      (_SECURITY_BASE + "/decryption-rules/{id}",      "id",      _GET_BY_ID_SCHEMA),
    "get_app_override_rule":    (_SECURITY_BASE + "/app-override-rules/{id}",    "id",      _GET_BY_ID_SCHEMA),
    "get_dos_protection_rule":  (_SECURITY_BASE + "/dos-protection-rules/{id}",  "id",      _GET_BY_ID_SCHEMA),

    # === B2 Security profiles (16 — url_filtering_categories has no get-by-id) ===
    "get_anti_spyware_profile":              (_SECURITY_BASE + "/anti-spyware-profiles/{id}",              "id", _GET_BY_ID_SCHEMA),
    "get_anti_spyware_signature":            (_SECURITY_BASE + "/anti-spyware-signatures/{id}",            "id", _GET_BY_ID_SCHEMA),
    "get_data_filtering_profile":            (_SECURITY_BASE + "/data-filtering-profiles/{id}",            "id", _GET_BY_ID_SCHEMA),
    "get_data_object":                       (_SECURITY_BASE + "/data-objects/{id}",                       "id", _GET_BY_ID_SCHEMA),
    "get_decryption_exclusion":              (_SECURITY_BASE + "/decryption-exclusions/{id}",              "id", _GET_BY_ID_SCHEMA),
    "get_decryption_profile":                (_SECURITY_BASE + "/decryption-profiles/{id}",                "id", _GET_BY_ID_SCHEMA),
    "get_dns_security_profile":              (_SECURITY_BASE + "/dns-security-profiles/{id}",              "id", _GET_BY_ID_SCHEMA),
    "get_dos_protection_profile":            (_SECURITY_BASE + "/dos-protection-profiles/{id}",            "id", _GET_BY_ID_SCHEMA),
    "get_file_blocking_profile":             (_SECURITY_BASE + "/file-blocking-profiles/{id}",             "id", _GET_BY_ID_SCHEMA),
    "get_http_header_profile":               (_SECURITY_BASE + "/http-header-profiles/{id}",               "id", _GET_BY_ID_SCHEMA),
    "get_profile_group":                     (_SECURITY_BASE + "/profile-groups/{id}",                     "id", _GET_BY_ID_SCHEMA),
    "get_url_access_profile":                (_SECURITY_BASE + "/url-access-profiles/{id}",                "id", _GET_BY_ID_SCHEMA),
    "get_url_category":                      (_SECURITY_BASE + "/url-categories/{id}",                     "id", _GET_BY_ID_SCHEMA),
    "get_vulnerability_protection_profile":  (_SECURITY_BASE + "/vulnerability-protection-profiles/{id}",  "id", _GET_BY_ID_SCHEMA),
    "get_vulnerability_protection_signature":(_SECURITY_BASE + "/vulnerability-protection-signatures/{id}","id", _GET_BY_ID_SCHEMA),
    "get_wildfire_anti_virus_profile":       (_SECURITY_BASE + "/wildfire-anti-virus-profiles/{id}",       "id", _GET_BY_ID_SCHEMA),

    # === C1 Operations ===
    "get_job":            (_OPS_BASE + "/jobs/{id}",                   "id",      _GET_BY_ID_SCHEMA),
    "get_config_version": (_OPS_BASE + "/config-versions/{version}",  "version", _GET_BY_VERSION_SCHEMA),

    # === D1 IAM ===
    "get_service_account": ("/iam/v1/service_accounts/{id}", "id",   _GET_BY_ID_SCHEMA),
    "get_role":            ("/iam/v1/roles/{name}",          "name", _GET_BY_NAME_SCHEMA),
    "get_access_policy":   ("/iam/v1/access_policies/{id}",  "id",   _GET_BY_ID_SCHEMA),
}

# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

def _error(status: int, body: dict) -> dict:
    return {
        "error": body.get("_errors", body.get("error", str(body))),
        "status": status,
        "body": body,
    }

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def call(name: str, args: dict) -> dict | None:
    """
    Handle a read-only tool call.
    Returns None if the tool name is not in this module.
    """
    iam_base = _IAM_SASE_BASE if name in _IAM_TOOL_NAMES else None

    if name in _LIST_TOOLS:
        path, params_schema = _LIST_TOOLS[name]
        params = {k: v for k, v in args.items()
                  if k in params_schema.get("properties", {}) and v is not None}
        kwargs = {"params": params or None}
        if iam_base:
            kwargs["base"] = iam_base
        status, body = rest_client.request("GET", path, **kwargs)
        if status == 0 or status >= 400:
            return _error(status, body)
        return body

    if name in _GET_BY_ID_TOOLS:
        tmpl, id_key, _ = _GET_BY_ID_TOOLS[name]
        obj_id = args.get(id_key)
        if not obj_id:
            return {"error": f"Missing required parameter: {id_key}"}
        path = tmpl.replace(f"{{{id_key}}}", str(obj_id))
        kwargs = {}
        if iam_base:
            kwargs["base"] = iam_base
        status, body = rest_client.request("GET", path, **kwargs)
        if status == 0 or status >= 400:
            return _error(status, body)
        return body

    return None

# ---------------------------------------------------------------------------
# Tool descriptors (for server.py list_tools)
# ---------------------------------------------------------------------------

def _make_tool(name: str, description: str, schema: dict) -> types.Tool:
    return types.Tool(name=name, description=description, inputSchema=schema)


def list_tool_descriptors() -> list[types.Tool]:
    tools: list[types.Tool] = []

    for name, (path, params_schema) in _LIST_TOOLS.items():
        resource = name.removeprefix("list_").replace("_", " ")
        tools.append(_make_tool(name, f"List {resource}", params_schema))

    for name, (tmpl, id_key, schema) in _GET_BY_ID_TOOLS.items():
        resource = name.removeprefix("get_").replace("_", " ")
        tools.append(_make_tool(name, f"Get {resource} by {id_key}", schema))

    return tools
