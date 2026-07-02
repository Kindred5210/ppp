"""
Batch 1 특수 작업 구현.

  move_*             POST /{resource}/{id}:move
  push_candidate_config  POST /config-versions/candidate:push
  load_config_version    POST /config-versions:load
  delete_candidate_config DELETE /config-versions/candidate
  reset_service_account_secret POST /iam/v1/service_accounts/{id}/operations/reset

ref: security-services-R2-2026.yaml (move endpoints)
     config-operations-march.yaml (push/load/delete)
     ServiceAccounts.yaml (reset)
"""

from mcp import types
from scm_mcp_server import rest_client

_SECURITY_BASE = "/config/security/v1"
_OPS_BASE      = "/config/operations/v1"
_IAM_SASE_BASE = "https://api.sase.paloaltonetworks.com"

# ---------------------------------------------------------------------------
# _MOVE_TOOLS
# ref: security-services-R2-2026.yaml
#   POST /{resource}/{id}:move
#   body required: destination (enum), rulebase (enum)
#   body optional: destination_rule (string, required when destination=before|after)
# ---------------------------------------------------------------------------

_MOVE_TOOLS: dict[str, tuple[str, str]] = {
    # tool_name: (base_path, description_label)
    "move_security_rule":     (_SECURITY_BASE + "/security-rules",     "security rule"),
    "move_decryption_rule":   (_SECURITY_BASE + "/decryption-rules",   "decryption rule"),
    "move_app_override_rule": (_SECURITY_BASE + "/app-override-rules", "app-override rule"),
}

_MOVE_BODY_KEYS    = ("destination", "rulebase", "destination_rule")
_MOVE_REQUIRED     = ("destination", "rulebase")
_DESTINATION_ENUM  = ("top", "bottom", "before", "after")
_RULEBASE_ENUM     = ("pre", "post")

_MOVE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Rule UUID",
        },
        "destination": {
            "type": "string",
            "enum": list(_DESTINATION_ENUM),
            "description": "Where to move: top | bottom | before | after",
        },
        "rulebase": {
            "type": "string",
            "enum": list(_RULEBASE_ENUM),
            "description": "Rule base: pre | post",
        },
        "destination_rule": {
            "type": "string",
            "description": "Target rule UUID — required when destination is before or after",
        },
    },
    "required": ["id", "destination", "rulebase"],
}

# ---------------------------------------------------------------------------
# Operations special schemas
# ref: config-operations-march.yaml
# ---------------------------------------------------------------------------

# POST /config-versions:load — body: {version: integer}
_LOAD_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "version": {"type": "integer", "description": "Config version number to load"},
    },
    "required": ["version"],
}

# POST /config-versions/candidate:push
# body: folder (array) | devices (array), plus optional admin (array), description (string)
# ref: allOf[folders|devices] — folder and devices are mutually exclusive target specifiers
_PUSH_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "folder": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Target folders (e.g. [\"Shared\", \"Mobile Users\"]). Mutually exclusive with devices.",
        },
        "devices": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Target device serial numbers. Mutually exclusive with folder.",
        },
        "admin": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Administrators or service accounts whose changes to push.",
        },
        "description": {
            "type": "string",
            "description": "Description of the changes being pushed.",
        },
    },
    "required": [],
}

# ---------------------------------------------------------------------------
# Helpers
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

    # --- move_* ---
    if name in _MOVE_TOOLS:
        base_path, _ = _MOVE_TOOLS[name]
        obj_id = args.get("id")
        if not obj_id:
            return {"error": "Missing required parameter: id"}
        missing = [k for k in _MOVE_REQUIRED if not args.get(k)]
        if missing:
            return {"error": f"Missing required parameter(s): {', '.join(missing)}"}
        body = {k: args[k] for k in _MOVE_BODY_KEYS if args.get(k) is not None}
        path = f"{base_path}/{obj_id}:move"
        status, resp = rest_client.request("POST", path, json=body)
        if status == 0 or status >= 400:
            return _error(status, resp)
        return resp

    # --- push_candidate_config ---
    if name == "push_candidate_config":
        body = {k: v for k, v in args.items()
                if k in ("folder", "devices", "admin", "description") and v is not None}
        status, resp = rest_client.request(
            "POST", _OPS_BASE + "/config-versions/candidate:push", json=body
        )
        if status == 0 or status >= 400:
            return _error(status, resp)
        return resp

    # --- load_config_version ---
    if name == "load_config_version":
        version = args.get("version")
        if version is None:
            return {"error": "Missing required parameter: version"}
        body = {"version": version}
        status, resp = rest_client.request(
            "POST", _OPS_BASE + "/config-versions:load", json=body
        )
        if status == 0 or status >= 400:
            return _error(status, resp)
        return resp

    # --- delete_candidate_config ---
    if name == "delete_candidate_config":
        status, resp = rest_client.request(
            "DELETE", _OPS_BASE + "/config-versions/candidate"
        )
        if status == 0 or status >= 400:
            return _error(status, resp)
        return resp

    # --- reset_service_account_secret ---
    if name == "reset_service_account_secret":
        obj_id = args.get("id")
        if not obj_id:
            return {"error": "Missing required parameter: id"}
        path = f"/iam/v1/service_accounts/{obj_id}/operations/reset"
        status, resp = rest_client.request(
            "POST", path, base=_IAM_SASE_BASE
        )
        if status == 0 or status >= 400:
            return _error(status, resp)
        return resp

    return None

# ---------------------------------------------------------------------------
# Tool descriptors
# ---------------------------------------------------------------------------

def list_tool_descriptors() -> list[types.Tool]:
    tools: list[types.Tool] = []

    # move_* tools
    for name, (_, label) in _MOVE_TOOLS.items():
        tools.append(types.Tool(
            name=name,
            description=(
                f"⚠️ 写操作，会改变规则顺序 — Move a {label} "
                f"(destination: top/bottom/before/after, rulebase: pre/post). "
                f"立即生效，不可通过本工具回滚。"
            ),
            inputSchema=_MOVE_SCHEMA,
        ))

    # push_candidate_config
    tools.append(types.Tool(
        name="push_candidate_config",
        description=(
            "⚠️ 高风险写操作：会将候选配置下发到真实设备 — "
            "Push candidate config to target folders or devices. "
            "此操作立即触发配置部署，不可通过本工具回滚。"
        ),
        inputSchema=_PUSH_SCHEMA,
    ))

    # load_config_version
    tools.append(types.Tool(
        name="load_config_version",
        description=(
            "⚠️ 写操作 — Load a specific config version as the candidate. "
            "立即生效，不可通过本工具回滚。"
        ),
        inputSchema=_LOAD_SCHEMA,
    ))

    # delete_candidate_config
    tools.append(types.Tool(
        name="delete_candidate_config",
        description=(
            "⚠️ 写操作 — Delete the current candidate configuration. "
            "立即生效，不可通过本工具回滚。"
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ))

    # reset_service_account_secret
    tools.append(types.Tool(
        name="reset_service_account_secret",
        description=(
            "⚠️ 写操作 — Reset the client secret of a service account by ID. "
            "旧 secret 立即失效，不可通过本工具回滚。"
        ),
        inputSchema={
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Service account UUID"}},
            "required": ["id"],
        },
    ))

    return tools
