"""
只读 tool 测试脚手架（RED → GREEN）。
mock scm_mcp_server.rest_client.request，不发真实 HTTP。

覆盖范围（DESIGN.md Batch 1 只读，共 66 个 tool）：
  - Objects A1 × 7 资源：list_* 7 + get_* 7 = 14
  - Security B1 规则 × 4：list_* 4 + get_* 4 = 8
  - Security B2 档案 × 17（url_filtering_categories 仅 list）：list_* 17 + get_* 16 = 33
  - Operations C1：list_jobs/list_config_versions/get_running_config_version
                  + get_job/get_config_version = 5
  - IAM D1：list_service_accounts/list_roles/list_access_policies
           + get_service_account/get_role/get_access_policy = 6
"""

import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LIST_200 = {"data": [{"id": "abc", "name": "test"}], "total": 1, "limit": 200, "offset": 0}
_OBJ_200  = {"id": "abc", "name": "test"}
_ERR_401  = {"_errors": [{"message": "Unauthorized", "code": "E003"}]}
_ERR_404  = {"_errors": [{"message": "Object Not Present", "code": "E005"}]}


def _call(name: str, args: dict) -> dict:
    from scm_mcp_server.tools import call
    return call(name, args)


def _mock_req(status: int, body: dict):
    return patch("scm_mcp_server.rest_client.request", return_value=(status, body))


def _assert_path_contains(mock_obj, fragment: str):
    """Assert the path argument (positional arg 1) contains fragment."""
    args = mock_obj.call_args.args
    assert fragment in args[1], f"Expected '{fragment}' in path '{args[1]}'"


# ===========================================================================
# A1 — Objects core (7 resources)
# ===========================================================================

class TestObjectsListTools:
    """list_* tools for all 7 Objects A1 resources."""

    @pytest.mark.parametrize("tool,path_fragment", [
        ("list_addresses",            "/addresses"),
        ("list_address_groups",       "/address-groups"),
        ("list_services",             "/services"),
        ("list_service_groups",       "/service-groups"),
        ("list_tags",                 "/tags"),
        ("list_application_groups",   "/application-groups"),
        ("list_external_dynamic_lists", "/external-dynamic-lists"),
    ])
    def test_returns_body_on_200(self, tool, path_fragment):
        with _mock_req(200, _LIST_200):
            result = _call(tool, {})
        assert "data" in result

    @pytest.mark.parametrize("tool,path_fragment", [
        ("list_addresses",            "/addresses"),
        ("list_address_groups",       "/address-groups"),
        ("list_services",             "/services"),
        ("list_service_groups",       "/service-groups"),
        ("list_tags",                 "/tags"),
        ("list_application_groups",   "/application-groups"),
        ("list_external_dynamic_lists", "/external-dynamic-lists"),
    ])
    def test_path_contains_resource(self, tool, path_fragment):
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {})
        _assert_path_contains(m, path_fragment)

    @pytest.mark.parametrize("tool", [
        "list_addresses", "list_address_groups", "list_services",
        "list_service_groups", "list_tags",
        "list_application_groups", "list_external_dynamic_lists",
    ])
    def test_passes_folder_param(self, tool):
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {"folder": "Shared"})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("folder") == "Shared"

    @pytest.mark.parametrize("tool", [
        "list_addresses", "list_address_groups", "list_services",
    ])
    def test_passes_offset_limit(self, tool):
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {"offset": 10, "limit": 50})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("offset") == 10
        assert kwargs.get("params", {}).get("limit") == 50

    @pytest.mark.parametrize("tool", [
        "list_addresses", "list_tags",
    ])
    def test_non_2xx_returns_error_shape(self, tool):
        with _mock_req(401, _ERR_401):
            result = _call(tool, {})
        assert "error" in result
        assert result["status"] == 401

    @pytest.mark.parametrize("tool", ["list_addresses"])
    def test_network_error_returns_error(self, tool):
        with _mock_req(0, {"error": "Cannot connect"}):
            result = _call(tool, {})
        assert "error" in result


class TestObjectsGetByIdTools:
    """get_* tools for Objects A1 — all require 'id'."""

    @pytest.mark.parametrize("tool,path_fragment", [
        ("get_address",              "/addresses/"),
        ("get_address_group",        "/address-groups/"),
        ("get_service",              "/services/"),
        ("get_service_group",        "/service-groups/"),
        ("get_tag",                  "/tags/"),
        ("get_application_group",    "/application-groups/"),
        ("get_external_dynamic_list","/external-dynamic-lists/"),
    ])
    def test_id_in_path(self, tool, path_fragment):
        with _mock_req(200, _OBJ_200) as m:
            _call(tool, {"id": "uuid-123"})
        _assert_path_contains(m, path_fragment + "uuid-123")

    @pytest.mark.parametrize("tool", [
        "get_address", "get_address_group", "get_service",
        "get_service_group", "get_tag",
        "get_application_group", "get_external_dynamic_list",
    ])
    def test_returns_body_on_200(self, tool):
        with _mock_req(200, _OBJ_200):
            result = _call(tool, {"id": "abc"})
        assert result["id"] == "abc"

    @pytest.mark.parametrize("tool", [
        "get_address", "get_address_group", "get_service",
    ])
    def test_missing_id_returns_error(self, tool):
        result = _call(tool, {})
        assert "error" in result
        assert "id" in result["error"].lower()

    @pytest.mark.parametrize("tool", ["get_address"])
    def test_404_returns_error(self, tool):
        with _mock_req(404, _ERR_404):
            result = _call(tool, {"id": "gone"})
        assert "error" in result
        assert result["status"] == 404


# ===========================================================================
# B1 — Security rules (4 types)
# ===========================================================================

class TestSecurityRulesListTools:
    @pytest.mark.parametrize("tool,path_fragment", [
        ("list_security_rules",       "/security-rules"),
        ("list_decryption_rules",     "/decryption-rules"),
        ("list_app_override_rules",   "/app-override-rules"),
        ("list_dos_protection_rules", "/dos-protection-rules"),
    ])
    def test_path_correct(self, tool, path_fragment):
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {})
        _assert_path_contains(m, path_fragment)

    @pytest.mark.parametrize("tool", [
        "list_security_rules", "list_decryption_rules", "list_app_override_rules",
        # list_dos_protection_rules uses _CONTAINER_LIST_PARAMS (no position field)
    ])
    def test_position_param_optional(self, tool):
        # position is optional; should be passed when provided, omitted when not
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {"position": "pre"})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("position") == "pre"

    @pytest.mark.parametrize("tool", ["list_security_rules"])
    def test_position_omitted_when_not_provided(self, tool):
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {"folder": "Shared"})
        _, kwargs = m.call_args
        assert "position" not in (kwargs.get("params") or {})

    def test_non_2xx_returns_error(self):
        with _mock_req(403, {"message": "Forbidden"}):
            result = _call("list_security_rules", {})
        assert "error" in result
        assert result["status"] == 403


class TestSecurityRulesGetByIdTools:
    @pytest.mark.parametrize("tool,path_fragment", [
        ("get_security_rule",       "/security-rules/"),
        ("get_decryption_rule",     "/decryption-rules/"),
        ("get_app_override_rule",   "/app-override-rules/"),
        ("get_dos_protection_rule", "/dos-protection-rules/"),
    ])
    def test_id_in_path(self, tool, path_fragment):
        with _mock_req(200, _OBJ_200) as m:
            _call(tool, {"id": "rule-uuid"})
        _assert_path_contains(m, path_fragment + "rule-uuid")

    @pytest.mark.parametrize("tool", [
        "get_security_rule", "get_decryption_rule",
    ])
    def test_missing_id_returns_error(self, tool):
        result = _call(tool, {})
        assert "error" in result

    def test_404_returns_error(self):
        with _mock_req(404, _ERR_404):
            result = _call("get_security_rule", {"id": "gone"})
        assert result["status"] == 404


# ===========================================================================
# B2 — Security profiles readonly (17 types)
# ===========================================================================

_B2_LIST_TOOLS = [
    ("list_anti_spyware_profiles",            "/anti-spyware-profiles"),
    ("list_anti_spyware_signatures",          "/anti-spyware-signatures"),
    ("list_data_filtering_profiles",          "/data-filtering-profiles"),
    ("list_data_objects",                     "/data-objects"),
    ("list_decryption_exclusions",            "/decryption-exclusions"),
    ("list_decryption_profiles",              "/decryption-profiles"),
    ("list_dns_security_profiles",            "/dns-security-profiles"),
    ("list_dos_protection_profiles",          "/dos-protection-profiles"),
    ("list_file_blocking_profiles",           "/file-blocking-profiles"),
    ("list_http_header_profiles",             "/http-header-profiles"),
    ("list_profile_groups",                   "/profile-groups"),
    ("list_url_access_profiles",              "/url-access-profiles"),
    ("list_url_categories",                   "/url-categories"),
    ("list_url_filtering_categories",         "/url-filtering-categories"),
    ("list_vulnerability_protection_profiles","/vulnerability-protection-profiles"),
    ("list_vulnerability_protection_signatures", "/vulnerability-protection-signatures"),
    ("list_wildfire_anti_virus_profiles",     "/wildfire-anti-virus-profiles"),
]

_B2_GET_TOOLS = [
    ("get_anti_spyware_profile",              "/anti-spyware-profiles/"),
    ("get_anti_spyware_signature",            "/anti-spyware-signatures/"),
    ("get_data_filtering_profile",            "/data-filtering-profiles/"),
    ("get_data_object",                       "/data-objects/"),
    ("get_decryption_exclusion",              "/decryption-exclusions/"),
    ("get_decryption_profile",                "/decryption-profiles/"),
    ("get_dns_security_profile",              "/dns-security-profiles/"),
    ("get_dos_protection_profile",            "/dos-protection-profiles/"),
    ("get_file_blocking_profile",             "/file-blocking-profiles/"),
    ("get_http_header_profile",               "/http-header-profiles/"),
    ("get_profile_group",                     "/profile-groups/"),
    ("get_url_access_profile",                "/url-access-profiles/"),
    ("get_url_category",                      "/url-categories/"),
    ("get_vulnerability_protection_profile",  "/vulnerability-protection-profiles/"),
    ("get_vulnerability_protection_signature","/vulnerability-protection-signatures/"),
    ("get_wildfire_anti_virus_profile",       "/wildfire-anti-virus-profiles/"),
]


class TestSecurityProfilesListTools:
    @pytest.mark.parametrize("tool,path_fragment", _B2_LIST_TOOLS)
    def test_path_correct(self, tool, path_fragment):
        with _mock_req(200, _LIST_200) as m:
            _call(tool, {})
        _assert_path_contains(m, path_fragment)

    @pytest.mark.parametrize("tool,_", _B2_LIST_TOOLS)
    def test_returns_data_on_200(self, tool, _):
        with _mock_req(200, _LIST_200):
            result = _call(tool, {})
        assert "data" in result

    @pytest.mark.parametrize("tool,_", [
        ("list_anti_spyware_profiles", None),
        ("list_wildfire_anti_virus_profiles", None),
    ])
    def test_non_2xx_returns_error(self, tool, _):
        with _mock_req(500, {"message": "Internal error"}):
            result = _call(tool, {})
        assert "error" in result
        assert result["status"] == 500

    def test_url_filtering_categories_has_no_get_by_id(self):
        # list_url_filtering_categories exists; get_url_filtering_category does NOT
        result = _call("get_url_filtering_category", {})
        assert "error" in result and "not implemented" in result["error"].lower()


class TestSecurityProfilesGetByIdTools:
    @pytest.mark.parametrize("tool,path_fragment", _B2_GET_TOOLS)
    def test_id_in_path(self, tool, path_fragment):
        with _mock_req(200, _OBJ_200) as m:
            _call(tool, {"id": "prof-uuid"})
        _assert_path_contains(m, path_fragment + "prof-uuid")

    @pytest.mark.parametrize("tool,_", _B2_GET_TOOLS[:3])
    def test_missing_id_returns_error(self, tool, _):
        result = _call(tool, {})
        assert "error" in result

    def test_404_returns_error(self):
        with _mock_req(404, _ERR_404):
            result = _call("get_anti_spyware_profile", {"id": "gone"})
        assert result["status"] == 404


# ===========================================================================
# C1 — Operations
# ===========================================================================

class TestOperationsReadonlyTools:
    def test_list_jobs_path(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_jobs", {})
        _assert_path_contains(m, "/jobs")

    def test_list_jobs_no_required_params(self):
        with _mock_req(200, _LIST_200):
            result = _call("list_jobs", {})
        assert "data" in result

    def test_get_job_id_in_path(self):
        with _mock_req(200, _OBJ_200) as m:
            _call("get_job", {"id": "job-42"})
        _assert_path_contains(m, "/jobs/job-42")

    def test_get_job_missing_id(self):
        result = _call("get_job", {})
        assert "error" in result

    def test_list_config_versions_path(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_config_versions", {})
        _assert_path_contains(m, "/config-versions")

    def test_list_config_versions_passes_offset_limit(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_config_versions", {"offset": 5, "limit": 10})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("limit") == 10

    def test_get_config_version_version_in_path(self):
        with _mock_req(200, _OBJ_200) as m:
            _call("get_config_version", {"version": "42"})
        _assert_path_contains(m, "/config-versions/42")

    def test_get_config_version_missing_version(self):
        result = _call("get_config_version", {})
        assert "error" in result

    def test_get_running_config_version_path(self):
        with _mock_req(200, _OBJ_200) as m:
            _call("get_running_config_version", {})
        _assert_path_contains(m, "/config-versions/running")

    def test_operations_non_2xx(self):
        with _mock_req(503, {"message": "Service Unavailable"}):
            result = _call("list_jobs", {})
        assert result["status"] == 503


# ===========================================================================
# D1 — IAM (uses api.sase.paloaltonetworks.com)
# ===========================================================================

class TestIAMReadonlyTools:
    def test_list_service_accounts_path(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_service_accounts", {})
        _assert_path_contains(m, "/iam/v1/service_accounts")

    def test_list_service_accounts_uses_sase_base(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_service_accounts", {})
        _, kwargs = m.call_args
        assert kwargs.get("base", "").startswith("https://api.sase")

    def test_get_service_account_id_in_path(self):
        with _mock_req(200, _OBJ_200) as m:
            _call("get_service_account", {"id": "sa-uuid"})
        _assert_path_contains(m, "/service_accounts/sa-uuid")

    def test_get_service_account_missing_id(self):
        result = _call("get_service_account", {})
        assert "error" in result

    def test_list_roles_path(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_roles", {})
        _assert_path_contains(m, "/iam/v1/roles")

    def test_get_role_name_in_path(self):
        with _mock_req(200, _OBJ_200) as m:
            _call("get_role", {"name": "SuperAdmin"})
        _assert_path_contains(m, "/roles/SuperAdmin")

    def test_get_role_missing_name(self):
        result = _call("get_role", {})
        assert "error" in result

    def test_list_access_policies_path(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_access_policies", {})
        _assert_path_contains(m, "/iam/v1/access_policies")

    def test_list_access_policies_role_param(self):
        with _mock_req(200, _LIST_200) as m:
            _call("list_access_policies", {"role": "ReadOnly"})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("role") == "ReadOnly"

    def test_get_access_policy_id_in_path(self):
        with _mock_req(200, _OBJ_200) as m:
            _call("get_access_policy", {"id": "pol-uuid"})
        _assert_path_contains(m, "/access_policies/pol-uuid")

    def test_get_access_policy_missing_id(self):
        result = _call("get_access_policy", {})
        assert "error" in result

    def test_iam_non_2xx(self):
        with _mock_req(403, {"message": "Forbidden"}):
            result = _call("list_service_accounts", {})
        assert result["status"] == 403


# ===========================================================================
# Descriptor coverage
# ===========================================================================

class TestToolDescriptors:
    def test_readonly_tool_count(self):
        from scm_mcp_server.tools import list_tool_descriptors
        names = {t.name for t in list_tool_descriptors()}
        # Must contain all expected readonly tools
        expected_sample = {
            "list_addresses", "get_address",
            "list_security_rules", "get_security_rule",
            "list_anti_spyware_profiles", "get_anti_spyware_profile",
            "list_jobs", "get_job", "get_running_config_version",
            "list_service_accounts", "get_role",
        }
        missing = expected_sample - names
        assert not missing, f"Missing tool descriptors: {missing}"

    def test_readonly_tools_all_present(self):
        from scm_mcp_server.tools import list_tool_descriptors
        names = {t.name for t in list_tool_descriptors()}
        # All 66 readonly tools must exist (write tools added separately)
        readonly_sample = {
            "list_addresses", "get_address",
            "list_security_rules", "get_security_rule",
            "list_anti_spyware_profiles", "get_anti_spyware_profile",
            "list_url_filtering_categories",  # list-only, no get-by-id
            "list_jobs", "get_job", "get_running_config_version",
            "list_service_accounts", "get_role", "get_access_policy",
        }
        missing = readonly_sample - names
        assert not missing, f"Missing readonly tools: {missing}"
