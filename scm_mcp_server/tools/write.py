"""
Batch 1 표준 쓰기 작업 (create_* / update_* / delete_*).
move_* / push_* 등 특수 작업은 별도 모듈로 구현 예정.

라우트 테이블 구조:
  _CREATE_TOOLS : tool名 → (path, container_keys, body_keys, required_body_keys, position_in_query)
  _UPDATE_TOOLS : tool名 → (path_template, body_keys)
  _DELETE_TOOLS : tool名 → path_template

container_keys  = POST 시 query params로 분리할 컨테이너 필드 (folder/snippet/device)
body_keys       = YAML requestBody 스키마에 명시된 실제 body 필드 (readOnly 제외)
required_body_keys = 호출 전 반드시 있어야 하는 body 필드
position_in_query  = True일 때 position 값을 query param으로 분리

모든 inputSchema 는 대응 YAML 의 requestBody / parameters 에서 추출.
"""

from mcp import types
from scm_mcp_server import rest_client

_OBJECTS_BASE  = "/config/objects/v1"
_SECURITY_BASE = "/config/security/v1"
_IAM_SASE_BASE = "https://api.sase.paloaltonetworks.com"

_CONTAINER_KEYS = ("folder", "snippet", "device")

_IAM_WRITE_TOOLS = frozenset({
    "create_service_account", "update_service_account", "delete_service_account",
    "create_access_policy", "delete_access_policy",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(status: int, body: dict) -> dict:
    return {
        "error": body.get("_errors", body.get("error", str(body))),
        "status": status,
        "body": body,
    }


def _pick(args: dict, allowed_keys: tuple | list, exclude: tuple | list = ()) -> dict:
    """Return only provided non-None values that are in allowed_keys, minus exclude."""
    return {k: v for k, v in args.items()
            if k in allowed_keys and v is not None and k not in exclude}


# ---------------------------------------------------------------------------
# _CREATE_TOOLS
# ref: objects-june.yaml, security-services-R2-2026.yaml,
#      ServiceAccounts.yaml, AccessPolicies.yaml
#
# Format: (path, body_keys, required_body_keys, position_in_query)
# container fields (folder/snippet/device) always go to query params on POST.
# ---------------------------------------------------------------------------

_CREATE_TOOLS: dict[str, tuple[str, tuple, tuple, bool]] = {
    # === A1 Objects — ref: objects-june.yaml#/components/schemas/* ===

    # ref: objects-june.yaml#/components/schemas/addresses (anyOf: ip_netmask|ip_range|ip_wildcard|fqdn)
    "create_address": (
        _OBJECTS_BASE + "/addresses",
        ("name", "description", "tag", "ip_netmask", "ip_range", "ip_wildcard", "fqdn"),
        ("name",),
        False,
    ),
    # ref: objects-june.yaml#/components/schemas/address-groups (anyOf: static|dynamic)
    "create_address_group": (
        _OBJECTS_BASE + "/address-groups",
        ("name", "description", "tag", "static", "dynamic"),
        ("name",),
        False,
    ),
    # ref: objects-june.yaml#/components/schemas/services
    "create_service": (
        _OBJECTS_BASE + "/services",
        ("name", "description", "protocol", "tag"),
        ("name",),
        False,
    ),
    # ref: objects-june.yaml#/components/schemas/service-groups
    "create_service_group": (
        _OBJECTS_BASE + "/service-groups",
        ("name", "members", "tag"),
        ("name",),
        False,
    ),
    # ref: objects-june.yaml#/components/schemas/tags
    "create_tag": (
        _OBJECTS_BASE + "/tags",
        ("name", "color", "comments"),
        ("name",),
        False,
    ),
    # ref: objects-june.yaml#/components/schemas/application-groups
    "create_application_group": (
        _OBJECTS_BASE + "/application-groups",
        ("name", "members"),
        ("name",),
        False,
    ),
    # ref: objects-june.yaml#/components/schemas/external-dynamic-lists
    "create_external_dynamic_list": (
        _OBJECTS_BASE + "/external-dynamic-lists",
        ("name", "type"),
        ("name",),
        False,
    ),

    # === B1 Security rules — ref: security-services-R2-2026.yaml#/components/schemas/* ===

    # ref: security-services-R2-2026.yaml#/components/schemas/security-rules
    # position is a POST query param (ref: components/parameters/position)
    "create_security_rule": (
        _SECURITY_BASE + "/security-rules",
        ("name", "policy_type", "disabled", "description", "tag",
         "from", "to", "source", "negate_source", "source_user",
         "destination", "service", "schedule", "action",
         "negate_destination", "source_hip", "destination_hip",
         "application", "category", "profile_setting",
         "log_setting", "log_start", "log_end",
         "tenant_restrictions", "negate_user"),
        ("name",),
        True,   # position → query param
    ),
    # ref: security-services-R2-2026.yaml#/components/schemas/decryption-rules
    "create_decryption_rule": (
        _SECURITY_BASE + "/decryption-rules",
        ("name", "action", "description", "category", "destination",
         "destination_hip", "profile", "service", "source", "source_hip",
         "source_user", "tag", "from", "to", "disabled",
         "negate_source", "negate_destination", "log_setting",
         "log_fail", "log_success", "type"),
        ("name",),
        True,   # position → query param
    ),
    # ref: security-services-R2-2026.yaml#/components/schemas/app-override-rules
    "create_app_override_rule": (
        _SECURITY_BASE + "/app-override-rules",
        ("name", "application", "description", "destination", "disabled",
         "from", "group_tag", "negate_destination", "negate_source",
         "port", "protocol", "source", "tag", "to"),
        ("name",),
        True,   # position → query param
    ),
    # ref: security-services-R2-2026.yaml#/components/schemas/dos-protection-rules
    "create_dos_protection_rule": (
        _SECURITY_BASE + "/dos-protection-rules",
        ("name", "description", "disabled", "position", "schedule",
         "tag", "from", "to", "source", "source_user",
         "destination", "service", "action", "protection", "log_setting"),
        ("name",),
        False,  # dos-protection-rules POST has no position query param
    ),

    # === D1 IAM — ref: ServiceAccounts.yaml, AccessPolicies.yaml ===

    # ref: ServiceAccounts.yaml (POST /iam/v1/service_accounts)
    "create_service_account": (
        "/iam/v1/service_accounts",
        ("name", "contact_email", "description"),
        ("name",),
        False,
    ),
    # ref: AccessPolicies.yaml (POST /iam/v1/access_policies)
    "create_access_policy": (
        "/iam/v1/access_policies",
        ("principal", "resource", "role"),
        ("principal", "role", "resource"),
        False,
    ),
}

# ---------------------------------------------------------------------------
# _UPDATE_TOOLS: (path_template, body_keys)
# id always in path; container fields (folder/snippet/device) always excluded from body.
# ---------------------------------------------------------------------------

_UPDATE_TOOLS: dict[str, tuple[str, tuple]] = {
    # Objects
    "update_address": (
        _OBJECTS_BASE + "/addresses/{id}",
        ("name", "description", "tag", "ip_netmask", "ip_range", "ip_wildcard", "fqdn"),
    ),
    "update_address_group": (
        _OBJECTS_BASE + "/address-groups/{id}",
        ("name", "description", "tag", "static", "dynamic"),
    ),
    "update_service": (
        _OBJECTS_BASE + "/services/{id}",
        ("name", "description", "protocol", "tag"),
    ),
    "update_service_group": (
        _OBJECTS_BASE + "/service-groups/{id}",
        ("name", "members", "tag"),
    ),
    "update_tag": (
        _OBJECTS_BASE + "/tags/{id}",
        ("name", "color", "comments"),
    ),
    "update_application_group": (
        _OBJECTS_BASE + "/application-groups/{id}",
        ("name", "members"),
    ),
    "update_external_dynamic_list": (
        _OBJECTS_BASE + "/external-dynamic-lists/{id}",
        ("name", "type"),
    ),
    # Security rules
    "update_security_rule": (
        _SECURITY_BASE + "/security-rules/{id}",
        ("name", "policy_type", "disabled", "description", "tag",
         "from", "to", "source", "negate_source", "source_user",
         "destination", "service", "schedule", "action",
         "negate_destination", "source_hip", "destination_hip",
         "application", "category", "profile_setting",
         "log_setting", "log_start", "log_end",
         "tenant_restrictions", "negate_user"),
    ),
    "update_decryption_rule": (
        _SECURITY_BASE + "/decryption-rules/{id}",
        ("name", "action", "description", "category", "destination",
         "destination_hip", "profile", "service", "source", "source_hip",
         "source_user", "tag", "from", "to", "disabled",
         "negate_source", "negate_destination", "log_setting",
         "log_fail", "log_success", "type"),
    ),
    "update_app_override_rule": (
        _SECURITY_BASE + "/app-override-rules/{id}",
        ("name", "application", "description", "destination", "disabled",
         "from", "group_tag", "negate_destination", "negate_source",
         "port", "protocol", "source", "tag", "to"),
    ),
    "update_dos_protection_rule": (
        _SECURITY_BASE + "/dos-protection-rules/{id}",
        ("name", "description", "disabled", "position", "schedule",
         "tag", "from", "to", "source", "source_user",
         "destination", "service", "action", "protection", "log_setting"),
    ),
    # IAM
    "update_service_account": (
        "/iam/v1/service_accounts/{id}",
        ("contact_email", "description"),
    ),
}

# ---------------------------------------------------------------------------
# _DELETE_TOOLS: path_template only
# ---------------------------------------------------------------------------

_DELETE_TOOLS: dict[str, str] = {
    # Objects
    "delete_address":              _OBJECTS_BASE + "/addresses/{id}",
    "delete_address_group":        _OBJECTS_BASE + "/address-groups/{id}",
    "delete_service":              _OBJECTS_BASE + "/services/{id}",
    "delete_service_group":        _OBJECTS_BASE + "/service-groups/{id}",
    "delete_tag":                  _OBJECTS_BASE + "/tags/{id}",
    "delete_application_group":    _OBJECTS_BASE + "/application-groups/{id}",
    "delete_external_dynamic_list":_OBJECTS_BASE + "/external-dynamic-lists/{id}",
    # Security rules
    "delete_security_rule":        _SECURITY_BASE + "/security-rules/{id}",
    "delete_decryption_rule":      _SECURITY_BASE + "/decryption-rules/{id}",
    "delete_app_override_rule":    _SECURITY_BASE + "/app-override-rules/{id}",
    "delete_dos_protection_rule":  _SECURITY_BASE + "/dos-protection-rules/{id}",
    # IAM
    "delete_service_account":      "/iam/v1/service_accounts/{id}",
    "delete_access_policy":        "/iam/v1/access_policies/{id}",
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def call(name: str, args: dict) -> dict | None:
    iam_base = _IAM_SASE_BASE if name in _IAM_WRITE_TOOLS else None

    # --- create ---
    if name in _CREATE_TOOLS:
        path, body_keys, required_keys, position_in_query = _CREATE_TOOLS[name]

        missing = [k for k in required_keys if not args.get(k)]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}

        # container fields → query params
        params = _pick(args, _CONTAINER_KEYS)

        # position → query param if this resource uses it
        if position_in_query and args.get("position") is not None:
            params["position"] = args["position"]

        body = _pick(args, body_keys, exclude=_CONTAINER_KEYS)

        kwargs: dict = {"params": params or None, "json": body}
        if iam_base:
            kwargs["base"] = iam_base

        status, resp_body = rest_client.request("POST", path, **kwargs)
        if status == 0 or status >= 400:
            return _error(status, resp_body)
        return resp_body

    # --- update ---
    if name in _UPDATE_TOOLS:
        path_tmpl, body_keys = _UPDATE_TOOLS[name]
        obj_id = args.get("id")
        if not obj_id:
            return {"error": "Missing required parameter: id"}

        path = path_tmpl.replace("{id}", str(obj_id))
        body = _pick(args, body_keys, exclude=(*_CONTAINER_KEYS, "id"))

        kwargs = {"json": body}
        if iam_base:
            kwargs["base"] = iam_base

        status, resp_body = rest_client.request("PUT", path, **kwargs)
        if status == 0 or status >= 400:
            return _error(status, resp_body)
        return resp_body

    # --- delete ---
    if name in _DELETE_TOOLS:
        path_tmpl = _DELETE_TOOLS[name]
        obj_id = args.get("id")
        if not obj_id:
            return {"error": "Missing required parameter: id"}

        path = path_tmpl.replace("{id}", str(obj_id))
        kwargs = {}
        if iam_base:
            kwargs["base"] = iam_base

        status, resp_body = rest_client.request("DELETE", path, **kwargs)
        if status == 0 or status >= 400:
            return _error(status, resp_body)
        return resp_body

    return None

# ---------------------------------------------------------------------------
# Tool descriptors
# ---------------------------------------------------------------------------

def _schema_from_body_keys(body_keys: tuple, required_keys: tuple,
                            with_container: bool = True) -> dict:
    props: dict = {}
    if with_container:
        props["folder"]  = {"type": "string", "description": "Container: folder name"}
        props["snippet"] = {"type": "string", "description": "Container: snippet name"}
        props["device"]  = {"type": "string", "description": "Container: device name"}
    for k in body_keys:
        props[k] = {"type": "string", "description": k.replace("_", " ")}
    return {
        "type": "object",
        "properties": props,
        "required": list(required_keys),
    }


def list_tool_descriptors() -> list[types.Tool]:
    tools: list[types.Tool] = []

    for name, (path, body_keys, required_keys, _) in _CREATE_TOOLS.items():
        resource = name.removeprefix("create_").replace("_", " ")
        schema = _schema_from_body_keys(body_keys, required_keys,
                                         with_container=name not in _IAM_WRITE_TOOLS)
        tools.append(types.Tool(
            name=name,
            description=f"⚠️ 写操作 — Create a {resource}. 立即生效，不可通过本工具回滚",
            inputSchema=schema,
        ))

    for name, (path_tmpl, body_keys) in _UPDATE_TOOLS.items():
        resource = name.removeprefix("update_").replace("_", " ")
        props = {"id": {"type": "string", "description": "Object UUID (required)"}}
        for k in body_keys:
            props[k] = {"type": "string", "description": k.replace("_", " ")}
        tools.append(types.Tool(
            name=name,
            description=f"⚠️ 写操作 — Update a {resource} by ID. 立即生效，不可通过本工具回滚",
            inputSchema={"type": "object", "properties": props, "required": ["id"]},
        ))

    for name, path_tmpl in _DELETE_TOOLS.items():
        resource = name.removeprefix("delete_").replace("_", " ")
        tools.append(types.Tool(
            name=name,
            description=f"⚠️ 写操作 — Delete a {resource} by ID. 立即生效，不可通过本工具回滚",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string", "description": "Object UUID"}},
                "required": ["id"],
            },
        ))

    return tools
