"""
Batch 1 write tool 테스트 (create_* / update_* / delete_*).
mock rest_client.request — 실제 SCM 호출 없음.

@integration 마커: 실제 凭据가 있을 때만 실행 (부작용 주의).
본 파일은 단위 테스트만 포함 — 모두 mock 기반.

커버리지 (DESIGN.md Batch 1 쓰기 작업):
  Objects  : addresses, address_groups, services, service_groups,
             tags, application_groups, external_dynamic_lists (각 3 = 21)
  Security : security_rules, decryption_rules, app_override_rules,
             dos_protection_rules (각 3 = 12)
  IAM      : service_accounts (3), access_policies (2) = 5
  합계: 38 tools
"""

import pytest
from unittest.mock import patch, call as mock_call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call(name: str, args: dict) -> dict:
    from scm_mcp_server.tools import call
    return call(name, args)


def _mock(status: int, body: dict):
    return patch("scm_mcp_server.rest_client.request", return_value=(status, body))


_CREATED = {"id": "new-uuid", "name": "test-obj"}
_UPDATED = {"id": "abc",      "name": "updated-obj"}
_DELETED = {"message": "Object deleted successfully"}
_ERR_400 = {"_errors": [{"message": "Bad Request"}]}
_ERR_404 = {"_errors": [{"message": "Object Not Present"}]}


def _assert_method_path(mock_obj, method: str, path_fragment: str):
    args = mock_obj.call_args.args
    assert args[0].upper() == method.upper(), f"Expected {method}, got {args[0]}"
    assert path_fragment in args[1], f"Expected '{path_fragment}' in path '{args[1]}'"


# ===========================================================================
# Addresses
# ===========================================================================

class TestCreateAddress:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_address", {"name": "test", "ip_netmask": "10.0.0.0/8",
                                      "folder": "Shared"})
        _assert_method_path(m, "POST", "/addresses")

    def test_folder_in_query_params(self):
        with _mock(201, _CREATED) as m:
            _call("create_address", {"name": "a", "folder": "Shared",
                                      "ip_netmask": "1.0.0.0/8"})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("folder") == "Shared"

    def test_body_contains_name_and_address_field(self):
        with _mock(201, _CREATED) as m:
            _call("create_address", {"name": "a", "ip_netmask": "1.0.0.0/8",
                                      "folder": "Shared"})
        _, kwargs = m.call_args
        body = kwargs.get("json", {})
        assert body["name"] == "a"
        assert body["ip_netmask"] == "1.0.0.0/8"

    def test_body_excludes_none_fields(self):
        with _mock(201, _CREATED) as m:
            _call("create_address", {"name": "a", "folder": "Shared",
                                      "ip_netmask": "1.0.0.0/8"})
        _, kwargs = m.call_args
        body = kwargs.get("json", {})
        assert "description" not in body
        assert "tag" not in body

    def test_missing_name_returns_error(self):
        result = _call("create_address", {"folder": "Shared", "ip_netmask": "1.0.0.0/8"})
        assert "error" in result

    def test_non_2xx_returns_error(self):
        with _mock(400, _ERR_400):
            result = _call("create_address", {"name": "a", "folder": "Shared",
                                               "ip_netmask": "1.0.0.0/8"})
        assert result["status"] == 400


class TestUpdateAddress:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_address", {"id": "abc", "name": "updated"})
        _assert_method_path(m, "PUT", "/addresses/abc")

    def test_body_only_has_provided_fields(self):
        with _mock(200, _UPDATED) as m:
            _call("update_address", {"id": "abc", "name": "n", "description": "d"})
        _, kwargs = m.call_args
        body = kwargs.get("json", {})
        assert body["name"] == "n"
        assert body["description"] == "d"
        assert "tag" not in body

    def test_pick_excludes_id_and_container(self):
        with _mock(200, _UPDATED) as m:
            _call("update_address", {"id": "abc", "name": "n",
                                      "folder": "X", "snippet": "Y"})
        _, kwargs = m.call_args
        body = kwargs.get("json", {})
        assert "id" not in body
        assert "folder" not in body
        assert "snippet" not in body

    def test_missing_id_returns_error(self):
        result = _call("update_address", {"name": "n"})
        assert "error" in result
        assert "id" in result["error"].lower()

    def test_non_2xx_returns_error(self):
        with _mock(404, _ERR_404):
            result = _call("update_address", {"id": "gone", "name": "n"})
        assert result["status"] == 404


class TestDeleteAddress:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_address", {"id": "abc"})
        _assert_method_path(m, "DELETE", "/addresses/abc")

    def test_no_body(self):
        with _mock(200, _DELETED) as m:
            _call("delete_address", {"id": "abc"})
        _, kwargs = m.call_args
        assert kwargs.get("json") is None

    def test_missing_id_returns_error(self):
        result = _call("delete_address", {})
        assert "error" in result

    def test_non_2xx_returns_error(self):
        with _mock(404, _ERR_404):
            result = _call("delete_address", {"id": "gone"})
        assert result["status"] == 404


# ===========================================================================
# Address Groups
# ===========================================================================

class TestCreateAddressGroup:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_address_group", {"name": "g", "static": ["addr1"],
                                            "folder": "Shared"})
        _assert_method_path(m, "POST", "/address-groups")

    def test_static_members_in_body(self):
        with _mock(201, _CREATED) as m:
            _call("create_address_group", {"name": "g", "static": ["a", "b"],
                                            "folder": "Shared"})
        _, kwargs = m.call_args
        assert kwargs["json"]["static"] == ["a", "b"]

    def test_missing_name_returns_error(self):
        result = _call("create_address_group", {"static": ["a"], "folder": "Shared"})
        assert "error" in result


class TestUpdateAddressGroup:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_address_group", {"id": "g1", "name": "grp"})
        _assert_method_path(m, "PUT", "/address-groups/g1")

    def test_missing_id_returns_error(self):
        result = _call("update_address_group", {"name": "g"})
        assert "error" in result


class TestDeleteAddressGroup:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_address_group", {"id": "g1"})
        _assert_method_path(m, "DELETE", "/address-groups/g1")

    def test_missing_id_returns_error(self):
        result = _call("delete_address_group", {})
        assert "error" in result


# ===========================================================================
# Services
# ===========================================================================

class TestCreateService:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_service", {"name": "http",
                                      "protocol": {"tcp": {"port": "80"}},
                                      "folder": "Shared"})
        _assert_method_path(m, "POST", "/services")

    def test_protocol_in_body(self):
        with _mock(201, _CREATED) as m:
            _call("create_service", {"name": "http",
                                      "protocol": {"tcp": {"port": "80"}},
                                      "folder": "Shared"})
        _, kwargs = m.call_args
        assert kwargs["json"]["protocol"]["tcp"]["port"] == "80"

    def test_missing_name_returns_error(self):
        result = _call("create_service", {"folder": "Shared"})
        assert "error" in result


class TestUpdateService:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_service", {"id": "s1", "name": "http"})
        _assert_method_path(m, "PUT", "/services/s1")

    def test_missing_id_returns_error(self):
        result = _call("update_service", {"name": "s"})
        assert "error" in result


class TestDeleteService:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_service", {"id": "s1"})
        _assert_method_path(m, "DELETE", "/services/s1")

    def test_missing_id_returns_error(self):
        result = _call("delete_service", {})
        assert "error" in result


# ===========================================================================
# Service Groups
# ===========================================================================

class TestCreateServiceGroup:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_service_group", {"name": "sg",
                                            "members": ["http"],
                                            "folder": "Shared"})
        _assert_method_path(m, "POST", "/service-groups")

    def test_members_in_body(self):
        with _mock(201, _CREATED) as m:
            _call("create_service_group", {"name": "sg",
                                            "members": ["http", "https"],
                                            "folder": "Shared"})
        _, kwargs = m.call_args
        assert kwargs["json"]["members"] == ["http", "https"]

    def test_missing_name_returns_error(self):
        result = _call("create_service_group", {"members": ["http"], "folder": "Shared"})
        assert "error" in result


class TestUpdateServiceGroup:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_service_group", {"id": "sg1", "name": "sg",
                                            "members": ["http"]})
        _assert_method_path(m, "PUT", "/service-groups/sg1")

    def test_missing_id_returns_error(self):
        result = _call("update_service_group", {"name": "sg"})
        assert "error" in result


class TestDeleteServiceGroup:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_service_group", {"id": "sg1"})
        _assert_method_path(m, "DELETE", "/service-groups/sg1")

    def test_missing_id_returns_error(self):
        result = _call("delete_service_group", {})
        assert "error" in result


# ===========================================================================
# Tags
# ===========================================================================

class TestCreateTag:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_tag", {"name": "prod", "folder": "Shared"})
        _assert_method_path(m, "POST", "/tags")

    def test_color_in_body_when_provided(self):
        with _mock(201, _CREATED) as m:
            _call("create_tag", {"name": "t", "color": "Red", "folder": "Shared"})
        _, kwargs = m.call_args
        assert kwargs["json"]["color"] == "Red"

    def test_missing_name_returns_error(self):
        result = _call("create_tag", {"folder": "Shared"})
        assert "error" in result


class TestUpdateTag:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_tag", {"id": "t1", "name": "prod"})
        _assert_method_path(m, "PUT", "/tags/t1")

    def test_missing_id_returns_error(self):
        result = _call("update_tag", {"name": "t"})
        assert "error" in result


class TestDeleteTag:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_tag", {"id": "t1"})
        _assert_method_path(m, "DELETE", "/tags/t1")

    def test_missing_id_returns_error(self):
        result = _call("delete_tag", {})
        assert "error" in result


# ===========================================================================
# Application Groups
# ===========================================================================

class TestCreateApplicationGroup:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_application_group", {"name": "web-apps",
                                                "members": ["http"],
                                                "folder": "Shared"})
        _assert_method_path(m, "POST", "/application-groups")

    def test_missing_name_returns_error(self):
        result = _call("create_application_group", {"members": ["http"],
                                                     "folder": "Shared"})
        assert "error" in result


class TestUpdateApplicationGroup:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_application_group", {"id": "ag1", "name": "web"})
        _assert_method_path(m, "PUT", "/application-groups/ag1")

    def test_missing_id_returns_error(self):
        result = _call("update_application_group", {"name": "ag"})
        assert "error" in result


class TestDeleteApplicationGroup:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_application_group", {"id": "ag1"})
        _assert_method_path(m, "DELETE", "/application-groups/ag1")

    def test_missing_id_returns_error(self):
        result = _call("delete_application_group", {})
        assert "error" in result


# ===========================================================================
# External Dynamic Lists
# ===========================================================================

class TestCreateExternalDynamicList:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_external_dynamic_list", {"name": "edl",
                                                    "type": {"ip": {}},
                                                    "folder": "Shared"})
        _assert_method_path(m, "POST", "/external-dynamic-lists")

    def test_missing_name_returns_error(self):
        result = _call("create_external_dynamic_list", {"folder": "Shared"})
        assert "error" in result


class TestUpdateExternalDynamicList:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_external_dynamic_list", {"id": "edl1", "name": "edl"})
        _assert_method_path(m, "PUT", "/external-dynamic-lists/edl1")

    def test_missing_id_returns_error(self):
        result = _call("update_external_dynamic_list", {"name": "edl"})
        assert "error" in result


class TestDeleteExternalDynamicList:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_external_dynamic_list", {"id": "edl1"})
        _assert_method_path(m, "DELETE", "/external-dynamic-lists/edl1")

    def test_missing_id_returns_error(self):
        result = _call("delete_external_dynamic_list", {})
        assert "error" in result


# ===========================================================================
# Security Rules
# ===========================================================================

class TestCreateSecurityRule:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_security_rule", {
                "name": "allow-web", "folder": "Shared",
                "from": ["any"], "to": ["any"],
                "source": ["any"], "source_user": ["any"],
                "destination": ["any"], "service": ["any"],
                "action": "allow", "category": ["any"],
                "application": ["any"],
            })
        _assert_method_path(m, "POST", "/security-rules")

    def test_position_in_query_params_when_provided(self):
        with _mock(201, _CREATED) as m:
            _call("create_security_rule", {
                "name": "r", "folder": "Shared", "position": "pre",
                "from": ["any"], "to": ["any"], "source": ["any"],
                "source_user": ["any"], "destination": ["any"],
                "service": ["any"], "action": "allow",
                "category": ["any"], "application": ["any"],
            })
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("position") == "pre"

    def test_position_not_in_body(self):
        with _mock(201, _CREATED) as m:
            _call("create_security_rule", {
                "name": "r", "folder": "Shared", "position": "pre",
                "from": ["any"], "to": ["any"], "source": ["any"],
                "source_user": ["any"], "destination": ["any"],
                "service": ["any"], "action": "allow",
                "category": ["any"], "application": ["any"],
            })
        _, kwargs = m.call_args
        assert "position" not in kwargs.get("json", {})

    def test_missing_name_returns_error(self):
        result = _call("create_security_rule", {"folder": "Shared"})
        assert "error" in result

    def test_action_enum_in_body(self):
        with _mock(201, _CREATED) as m:
            _call("create_security_rule", {
                "name": "r", "folder": "Shared",
                "from": ["any"], "to": ["any"], "source": ["any"],
                "source_user": ["any"], "destination": ["any"],
                "service": ["any"], "action": "deny",
                "category": ["any"], "application": ["any"],
            })
        _, kwargs = m.call_args
        assert kwargs["json"]["action"] == "deny"


class TestUpdateSecurityRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_security_rule", {"id": "r1", "name": "updated"})
        _assert_method_path(m, "PUT", "/security-rules/r1")

    def test_pick_excludes_container_and_id(self):
        with _mock(200, _UPDATED) as m:
            _call("update_security_rule", {"id": "r1", "name": "n",
                                            "folder": "X", "snippet": "Y"})
        _, kwargs = m.call_args
        body = kwargs.get("json", {})
        assert "folder" not in body
        assert "id" not in body

    def test_missing_id_returns_error(self):
        result = _call("update_security_rule", {"name": "r"})
        assert "error" in result


class TestDeleteSecurityRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_security_rule", {"id": "r1"})
        _assert_method_path(m, "DELETE", "/security-rules/r1")

    def test_no_body(self):
        with _mock(200, _DELETED) as m:
            _call("delete_security_rule", {"id": "r1"})
        _, kwargs = m.call_args
        assert kwargs.get("json") is None

    def test_missing_id_returns_error(self):
        result = _call("delete_security_rule", {})
        assert "error" in result


# ===========================================================================
# Decryption Rules
# ===========================================================================

class TestCreateDecryptionRule:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_decryption_rule", {
                "name": "dr", "folder": "Shared",
                "action": "decrypt", "category": ["any"],
                "destination": ["any"], "service": ["any"],
                "source": ["any"], "source_user": ["any"],
                "from": ["any"], "to": ["any"],
            })
        _assert_method_path(m, "POST", "/decryption-rules")

    def test_missing_name_returns_error(self):
        result = _call("create_decryption_rule", {"folder": "Shared"})
        assert "error" in result


class TestUpdateDecryptionRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_decryption_rule", {"id": "dr1", "name": "dr"})
        _assert_method_path(m, "PUT", "/decryption-rules/dr1")

    def test_missing_id_returns_error(self):
        result = _call("update_decryption_rule", {"name": "dr"})
        assert "error" in result


class TestDeleteDecryptionRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_decryption_rule", {"id": "dr1"})
        _assert_method_path(m, "DELETE", "/decryption-rules/dr1")

    def test_missing_id_returns_error(self):
        result = _call("delete_decryption_rule", {})
        assert "error" in result


# ===========================================================================
# App Override Rules
# ===========================================================================

class TestCreateAppOverrideRule:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_app_override_rule", {"name": "aor",
                                                "folder": "Shared"})
        _assert_method_path(m, "POST", "/app-override-rules")

    def test_position_in_query_params(self):
        with _mock(201, _CREATED) as m:
            _call("create_app_override_rule", {"name": "aor",
                                                "folder": "Shared",
                                                "position": "post"})
        _, kwargs = m.call_args
        assert kwargs.get("params", {}).get("position") == "post"

    def test_missing_name_returns_error(self):
        result = _call("create_app_override_rule", {"folder": "Shared"})
        assert "error" in result


class TestUpdateAppOverrideRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_app_override_rule", {"id": "aor1", "name": "aor"})
        _assert_method_path(m, "PUT", "/app-override-rules/aor1")

    def test_missing_id_returns_error(self):
        result = _call("update_app_override_rule", {"name": "aor"})
        assert "error" in result


class TestDeleteAppOverrideRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_app_override_rule", {"id": "aor1"})
        _assert_method_path(m, "DELETE", "/app-override-rules/aor1")

    def test_missing_id_returns_error(self):
        result = _call("delete_app_override_rule", {})
        assert "error" in result


# ===========================================================================
# DoS Protection Rules
# ===========================================================================

class TestCreateDosProtectionRule:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_dos_protection_rule", {"name": "dpr",
                                                  "type": "aggregate",
                                                  "folder": "Shared"})
        _assert_method_path(m, "POST", "/dos-protection-rules")

    def test_missing_name_returns_error(self):
        result = _call("create_dos_protection_rule", {"folder": "Shared"})
        assert "error" in result


class TestUpdateDosProtectionRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_dos_protection_rule", {"id": "dpr1", "name": "dpr"})
        _assert_method_path(m, "PUT", "/dos-protection-rules/dpr1")

    def test_missing_id_returns_error(self):
        result = _call("update_dos_protection_rule", {"name": "dpr"})
        assert "error" in result


class TestDeleteDosProtectionRule:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_dos_protection_rule", {"id": "dpr1"})
        _assert_method_path(m, "DELETE", "/dos-protection-rules/dpr1")

    def test_missing_id_returns_error(self):
        result = _call("delete_dos_protection_rule", {})
        assert "error" in result


# ===========================================================================
# IAM — Service Accounts
# ===========================================================================

class TestCreateServiceAccount:
    def test_method_and_path_with_sase_base(self):
        with _mock(201, _CREATED) as m:
            _call("create_service_account", {"name": "sa1",
                                              "contact_email": "a@b.com"})
        _assert_method_path(m, "POST", "/iam/v1/service_accounts")
        _, kwargs = m.call_args
        assert kwargs.get("base", "").startswith("https://api.sase")

    def test_body_contains_name(self):
        with _mock(201, _CREATED) as m:
            _call("create_service_account", {"name": "sa1",
                                              "contact_email": "a@b.com"})
        _, kwargs = m.call_args
        assert kwargs["json"]["name"] == "sa1"

    def test_missing_name_returns_error(self):
        result = _call("create_service_account", {"contact_email": "a@b.com"})
        assert "error" in result


class TestUpdateServiceAccount:
    def test_method_and_id_in_path(self):
        with _mock(200, _UPDATED) as m:
            _call("update_service_account", {"id": "sa1",
                                              "description": "desc"})
        _assert_method_path(m, "PUT", "/iam/v1/service_accounts/sa1")

    def test_uses_sase_base(self):
        with _mock(200, _UPDATED) as m:
            _call("update_service_account", {"id": "sa1", "description": "d"})
        _, kwargs = m.call_args
        assert kwargs.get("base", "").startswith("https://api.sase")

    def test_missing_id_returns_error(self):
        result = _call("update_service_account", {"description": "d"})
        assert "error" in result


class TestDeleteServiceAccount:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_service_account", {"id": "sa1"})
        _assert_method_path(m, "DELETE", "/iam/v1/service_accounts/sa1")

    def test_missing_id_returns_error(self):
        result = _call("delete_service_account", {})
        assert "error" in result


# ===========================================================================
# IAM — Access Policies
# ===========================================================================

class TestCreateAccessPolicy:
    def test_method_and_path(self):
        with _mock(201, _CREATED) as m:
            _call("create_access_policy", {"principal": "user@domain.com",
                                            "role": "ReadOnly",
                                            "resource": "/"})
        _assert_method_path(m, "POST", "/iam/v1/access_policies")

    def test_uses_sase_base(self):
        with _mock(201, _CREATED) as m:
            _call("create_access_policy", {"principal": "u", "role": "r",
                                            "resource": "/"})
        _, kwargs = m.call_args
        assert kwargs.get("base", "").startswith("https://api.sase")

    def test_missing_required_field_returns_error(self):
        result = _call("create_access_policy", {"role": "ReadOnly"})
        assert "error" in result


class TestDeleteAccessPolicy:
    def test_method_and_id_in_path(self):
        with _mock(200, _DELETED) as m:
            _call("delete_access_policy", {"id": "pol1"})
        _assert_method_path(m, "DELETE", "/iam/v1/access_policies/pol1")

    def test_missing_id_returns_error(self):
        result = _call("delete_access_policy", {})
        assert "error" in result


# ===========================================================================
# Write tool descriptor checks
# ===========================================================================

class TestWriteToolDescriptors:
    def test_write_tools_present_in_descriptors(self):
        from scm_mcp_server.tools import list_tool_descriptors
        names = {t.name for t in list_tool_descriptors()}
        expected = {
            "create_address", "update_address", "delete_address",
            "create_security_rule", "update_security_rule", "delete_security_rule",
            "create_service_account", "delete_service_account",
            "create_access_policy", "delete_access_policy",
        }
        missing = expected - names
        assert not missing, f"Missing write tool descriptors: {missing}"

    def test_write_tool_descriptions_contain_warning(self):
        from scm_mcp_server.tools import list_tool_descriptors
        write_prefixes = ("create_", "update_", "delete_")
        for t in list_tool_descriptors():
            if t.name.startswith(write_prefixes):
                assert "⚠️" in t.description, \
                    f"{t.name} missing ⚠️ in description: {t.description!r}"

    def test_standard_write_tools_all_present(self):
        from scm_mcp_server.tools import list_tool_descriptors
        names = {t.name for t in list_tool_descriptors()}
        standard_writes = {
            "create_address", "update_address", "delete_address",
            "create_address_group", "update_address_group", "delete_address_group",
            "create_service", "update_service", "delete_service",
            "create_service_group", "update_service_group", "delete_service_group",
            "create_tag", "update_tag", "delete_tag",
            "create_application_group", "update_application_group", "delete_application_group",
            "create_external_dynamic_list", "update_external_dynamic_list", "delete_external_dynamic_list",
            "create_security_rule", "update_security_rule", "delete_security_rule",
            "create_decryption_rule", "update_decryption_rule", "delete_decryption_rule",
            "create_app_override_rule", "update_app_override_rule", "delete_app_override_rule",
            "create_dos_protection_rule", "update_dos_protection_rule", "delete_dos_protection_rule",
            "create_service_account", "update_service_account", "delete_service_account",
            "create_access_policy", "delete_access_policy",
        }
        missing = standard_writes - names
        assert not missing, f"Missing standard write tools: {missing}"
