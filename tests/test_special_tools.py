"""
Batch 1 특수 작업 + 수렴 검증 테스트.

특수 작업 (7개):
  move_security_rule / move_decryption_rule / move_app_override_rule
  push_candidate_config / load_config_version / delete_candidate_config
  reset_service_account_secret

수렴 검증:
  DESIGN.md Batch 1 전체 111개 tool 이름 == 등록된 tool 이름 집합
"""

import pytest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call(name: str, args: dict) -> dict:
    from scm_mcp_server.tools import call
    return call(name, args)


def _mock(status: int, body: dict):
    return patch("scm_mcp_server.rest_client.request", return_value=(status, body))


_OK   = {"success": True}
_MOVED = {"message": "moved"}
_ERR  = {"_errors": [{"message": "Bad Request"}]}

def _assert_method_path(mock_obj, method: str, fragment: str):
    args = mock_obj.call_args.args
    assert args[0].upper() == method, f"Expected {method}, got {args[0].upper()}"
    assert fragment in args[1], f"Expected '{fragment}' in '{args[1]}'"


# ===========================================================================
# move_* tools
# ===========================================================================

class TestMoveSecurityRule:
    def test_method_and_path_contains_move(self):
        with _mock(200, _MOVED) as m:
            _call("move_security_rule", {
                "id": "rule-1", "destination": "top", "rulebase": "pre"
            })
        _assert_method_path(m, "POST", "/security-rules/rule-1:move")

    def test_body_has_destination_and_rulebase(self):
        with _mock(200, _MOVED) as m:
            _call("move_security_rule", {
                "id": "r1", "destination": "bottom", "rulebase": "post"
            })
        _, kwargs = m.call_args
        body = kwargs.get("json", {})
        assert body["destination"] == "bottom"
        assert body["rulebase"] == "post"

    def test_destination_rule_optional(self):
        with _mock(200, _MOVED) as m:
            _call("move_security_rule", {
                "id": "r1", "destination": "before",
                "rulebase": "pre", "destination_rule": "rule-2"
            })
        _, kwargs = m.call_args
        assert kwargs["json"]["destination_rule"] == "rule-2"

    def test_destination_rule_omitted_when_not_provided(self):
        with _mock(200, _MOVED) as m:
            _call("move_security_rule", {
                "id": "r1", "destination": "top", "rulebase": "pre"
            })
        _, kwargs = m.call_args
        assert "destination_rule" not in kwargs["json"]

    def test_missing_id_returns_error(self):
        result = _call("move_security_rule", {"destination": "top", "rulebase": "pre"})
        assert "error" in result

    def test_missing_destination_returns_error(self):
        result = _call("move_security_rule", {"id": "r1", "rulebase": "pre"})
        assert "error" in result

    def test_missing_rulebase_returns_error(self):
        result = _call("move_security_rule", {"id": "r1", "destination": "top"})
        assert "error" in result

    def test_non_2xx_returns_error(self):
        with _mock(400, _ERR):
            result = _call("move_security_rule", {
                "id": "r1", "destination": "top", "rulebase": "pre"
            })
        assert result["status"] == 400

    def test_description_contains_warning(self):
        from scm_mcp_server.tools import list_tool_descriptors
        t = next(t for t in list_tool_descriptors() if t.name == "move_security_rule")
        assert "⚠️" in t.description


class TestMoveDecryptionRule:
    def test_method_and_path(self):
        with _mock(200, _MOVED) as m:
            _call("move_decryption_rule", {
                "id": "dr-1", "destination": "top", "rulebase": "pre"
            })
        _assert_method_path(m, "POST", "/decryption-rules/dr-1:move")

    def test_body_fields(self):
        with _mock(200, _MOVED) as m:
            _call("move_decryption_rule", {
                "id": "dr-1", "destination": "after",
                "rulebase": "post", "destination_rule": "dr-2"
            })
        _, kwargs = m.call_args
        assert kwargs["json"]["destination"] == "after"
        assert kwargs["json"]["destination_rule"] == "dr-2"

    def test_missing_id_returns_error(self):
        result = _call("move_decryption_rule", {"destination": "top", "rulebase": "pre"})
        assert "error" in result

    def test_missing_required_body_returns_error(self):
        result = _call("move_decryption_rule", {"id": "dr-1", "rulebase": "pre"})
        assert "error" in result


class TestMoveAppOverrideRule:
    def test_method_and_path(self):
        with _mock(200, _MOVED) as m:
            _call("move_app_override_rule", {
                "id": "aor-1", "destination": "bottom", "rulebase": "post"
            })
        _assert_method_path(m, "POST", "/app-override-rules/aor-1:move")

    def test_body_fields(self):
        with _mock(200, _MOVED) as m:
            _call("move_app_override_rule", {
                "id": "aor-1", "destination": "top", "rulebase": "pre"
            })
        _, kwargs = m.call_args
        assert kwargs["json"]["destination"] == "top"
        assert kwargs["json"]["rulebase"] == "pre"

    def test_missing_id_returns_error(self):
        result = _call("move_app_override_rule", {"destination": "top", "rulebase": "pre"})
        assert "error" in result

    def test_missing_required_body_returns_error(self):
        result = _call("move_app_override_rule", {"id": "aor-1", "destination": "top"})
        assert "error" in result


# ===========================================================================
# push_candidate_config
# ===========================================================================

class TestPushCandidateConfig:
    def test_method_and_path(self):
        with _mock(200, _OK) as m:
            _call("push_candidate_config", {"folder": ["Shared"]})
        _assert_method_path(m, "POST", "/config-versions/candidate:push")

    def test_folder_array_in_body(self):
        with _mock(200, _OK) as m:
            _call("push_candidate_config", {"folder": ["Shared", "Mobile Users"]})
        _, kwargs = m.call_args
        assert kwargs["json"]["folder"] == ["Shared", "Mobile Users"]

    def test_devices_array_in_body(self):
        with _mock(200, _OK) as m:
            _call("push_candidate_config", {"devices": ["007951000388704"]})
        _, kwargs = m.call_args
        assert kwargs["json"]["devices"] == ["007951000388704"]

    def test_admin_and_description_in_body(self):
        with _mock(200, _OK) as m:
            _call("push_candidate_config", {
                "folder": ["Shared"],
                "admin": ["admin@example.com"],
                "description": "deploy v2",
            })
        _, kwargs = m.call_args
        body = kwargs["json"]
        assert body["admin"] == ["admin@example.com"]
        assert body["description"] == "deploy v2"

    def test_none_fields_excluded_from_body(self):
        with _mock(200, _OK) as m:
            _call("push_candidate_config", {"folder": ["Shared"]})
        _, kwargs = m.call_args
        body = kwargs["json"]
        assert "devices" not in body
        assert "admin" not in body

    def test_non_2xx_returns_error(self):
        with _mock(500, {"message": "internal error"}):
            result = _call("push_candidate_config", {"folder": ["Shared"]})
        assert result["status"] == 500

    def test_description_contains_high_risk_warning(self):
        from scm_mcp_server.tools import list_tool_descriptors
        t = next(t for t in list_tool_descriptors() if t.name == "push_candidate_config")
        assert "⚠️" in t.description
        assert "高风险" in t.description or "候选配置" in t.description


# ===========================================================================
# load_config_version
# ===========================================================================

class TestLoadConfigVersion:
    def test_method_and_path(self):
        with _mock(200, _OK) as m:
            _call("load_config_version", {"version": 42})
        _assert_method_path(m, "POST", "/config-versions:load")

    def test_version_in_body(self):
        with _mock(200, _OK) as m:
            _call("load_config_version", {"version": 7})
        _, kwargs = m.call_args
        assert kwargs["json"]["version"] == 7

    def test_missing_version_returns_error(self):
        result = _call("load_config_version", {})
        assert "error" in result

    def test_non_2xx_returns_error(self):
        with _mock(400, _ERR):
            result = _call("load_config_version", {"version": 99})
        assert result["status"] == 400

    def test_description_contains_warning(self):
        from scm_mcp_server.tools import list_tool_descriptors
        t = next(t for t in list_tool_descriptors() if t.name == "load_config_version")
        assert "⚠️" in t.description


# ===========================================================================
# delete_candidate_config
# ===========================================================================

class TestDeleteCandidateConfig:
    def test_method_and_path(self):
        with _mock(200, _OK) as m:
            _call("delete_candidate_config", {})
        _assert_method_path(m, "DELETE", "/config-versions/candidate")

    def test_no_body(self):
        with _mock(200, _OK) as m:
            _call("delete_candidate_config", {})
        _, kwargs = m.call_args
        assert kwargs.get("json") is None

    def test_non_2xx_returns_error(self):
        with _mock(409, {"message": "Conflict"}):
            result = _call("delete_candidate_config", {})
        assert result["status"] == 409

    def test_description_contains_warning(self):
        from scm_mcp_server.tools import list_tool_descriptors
        t = next(t for t in list_tool_descriptors() if t.name == "delete_candidate_config")
        assert "⚠️" in t.description


# ===========================================================================
# reset_service_account_secret
# ===========================================================================

class TestResetServiceAccountSecret:
    def test_method_and_path(self):
        with _mock(200, _OK) as m:
            _call("reset_service_account_secret", {"id": "sa-1"})
        _assert_method_path(m, "POST", "/iam/v1/service_accounts/sa-1/operations/reset")

    def test_uses_sase_base(self):
        with _mock(200, _OK) as m:
            _call("reset_service_account_secret", {"id": "sa-1"})
        _, kwargs = m.call_args
        assert kwargs.get("base", "").startswith("https://api.sase")

    def test_no_body(self):
        with _mock(200, _OK) as m:
            _call("reset_service_account_secret", {"id": "sa-1"})
        _, kwargs = m.call_args
        assert kwargs.get("json") is None

    def test_missing_id_returns_error(self):
        result = _call("reset_service_account_secret", {})
        assert "error" in result

    def test_description_contains_warning(self):
        from scm_mcp_server.tools import list_tool_descriptors
        t = next(t for t in list_tool_descriptors() if t.name == "reset_service_account_secret")
        assert "⚠️" in t.description


# ===========================================================================
# Batch 1 수렴 검증
# ===========================================================================

BATCH1_TOOLS = frozenset("""
list_addresses get_address create_address update_address delete_address
list_address_groups get_address_group create_address_group update_address_group delete_address_group
list_services get_service create_service update_service delete_service
list_service_groups get_service_group create_service_group update_service_group delete_service_group
list_tags get_tag create_tag update_tag delete_tag
list_application_groups get_application_group create_application_group update_application_group delete_application_group
list_external_dynamic_lists get_external_dynamic_list create_external_dynamic_list update_external_dynamic_list delete_external_dynamic_list
list_security_rules get_security_rule create_security_rule update_security_rule delete_security_rule move_security_rule
list_decryption_rules get_decryption_rule create_decryption_rule update_decryption_rule delete_decryption_rule move_decryption_rule
list_app_override_rules get_app_override_rule create_app_override_rule update_app_override_rule delete_app_override_rule move_app_override_rule
list_dos_protection_rules get_dos_protection_rule create_dos_protection_rule update_dos_protection_rule delete_dos_protection_rule
list_anti_spyware_profiles get_anti_spyware_profile list_anti_spyware_signatures get_anti_spyware_signature
list_data_filtering_profiles get_data_filtering_profile list_data_objects get_data_object
list_decryption_exclusions get_decryption_exclusion list_decryption_profiles get_decryption_profile
list_dns_security_profiles get_dns_security_profile list_dos_protection_profiles get_dos_protection_profile
list_file_blocking_profiles get_file_blocking_profile list_http_header_profiles get_http_header_profile
list_profile_groups get_profile_group list_url_access_profiles get_url_access_profile
list_url_categories get_url_category list_url_filtering_categories
list_vulnerability_protection_profiles get_vulnerability_protection_profile
list_vulnerability_protection_signatures get_vulnerability_protection_signature
list_wildfire_anti_virus_profiles get_wildfire_anti_virus_profile
list_jobs get_job list_config_versions get_config_version get_running_config_version
load_config_version push_candidate_config delete_candidate_config
list_service_accounts get_service_account create_service_account update_service_account delete_service_account reset_service_account_secret
list_roles get_role list_access_policies get_access_policy create_access_policy delete_access_policy
""".split())


class TestBatch1Convergence:
    def test_no_missing_tools(self):
        from scm_mcp_server.tools import list_tool_descriptors
        registered = {t.name for t in list_tool_descriptors()}
        missing = BATCH1_TOOLS - registered
        assert not missing, (
            f"Batch 1 tools missing from registry ({len(missing)}):\n"
            + "\n".join(f"  {t}" for t in sorted(missing))
        )

    def test_no_extra_tools(self):
        from scm_mcp_server.tools import list_tool_descriptors
        registered = {t.name for t in list_tool_descriptors()}
        extra = registered - BATCH1_TOOLS
        assert not extra, (
            f"Registered tools not in Batch 1 ({len(extra)}):\n"
            + "\n".join(f"  {t}" for t in sorted(extra))
        )

    def test_total_count_is_111(self):
        from scm_mcp_server.tools import list_tool_descriptors
        count = len(list_tool_descriptors())
        assert count == 111, f"Expected 111 Batch-1 tools, got {count}"
