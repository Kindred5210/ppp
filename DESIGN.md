# DESIGN.md — L2 设计文档

## 1. 架构概览

```
Claude / Cursor
      │  MCP (stdio)
      ▼
 server.py  ──registers──►  tools/*.py
      │                          │
      │                     rest_client.py  (httpx)
      │                          │
      │                      auth.py        (token cache)
      │                          │
      └──────────────────────────►  SCM REST API
```

- **server.py**：MCP stdio loop，注册所有 tool handler。
- **auth.py**：OAuth2 client_credentials，token 内存缓存，到期前 60 s 自动刷新，threading.Lock 保证并发安全。
- **rest_client.py**：同步 httpx 包装，注入 `Authorization: Bearer <token>`，返回 `(status, body)`，不抛非 2xx。
- **tools/\*.py**：按资源域分组，每个函数对应一个 MCP tool，inputSchema 直接引用 YAML。

---

## 2. Schema 溯源规则

所有 tool 的 `inputSchema` 字段**必须**来自以下 YAML；不得手抄或臆造字段。

| YAML 文件路径 | base URL | 涵盖资源 |
|---|---|---|
| `openapi-specs/scm/config/sase/objects/objects-june.yaml` | `https://api.strata.paloaltonetworks.com/config/objects/v1` | 地址、地址组、服务、标签、应用、档案等对象 |
| `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml` | `https://api.strata.paloaltonetworks.com/config/security/v1` | 安全规则、解密规则、DoS 规则、所有安全档案 |
| `openapi-specs/scm/config/sase/operations/config-operations-march.yaml` | `https://api.strata.paloaltonetworks.com/config/operations/v1` | Jobs、配置版本 |
| `openapi-specs/scm/iam/ServiceAccounts.yaml` | `https://api.sase.paloaltonetworks.com` | IAM Service Accounts |
| `openapi-specs/scm/iam/Roles.yaml` | `https://api.sase.paloaltonetworks.com` | IAM Roles |
| `openapi-specs/scm/iam/AccessPolicies.yaml` | `https://api.sase.paloaltonetworks.com` | IAM Access Policies |
| `openapi-specs/scm/auth/AuthService.yaml` | `https://auth.apps.paloaltonetworks.com` | OAuth2 token（内部使用，不暴露为 tool） |

---

## 3. MCP Tool 映射表

### 实现批次说明

| 批次 | 内容 | Tool 数 | 状态 |
|------|------|---------|------|
| **Batch 1** | Objects 核心 + Security 规则 + Security 档案只读 + Operations 全部 + IAM 全部 | **111** | MVP |
| **Batch 2** | Objects 扩展 + Security 档案写操作 | **98** | 排期中 |
| **后续批次** | 非标模式对象、单例安全设置 | ~27 | 待确认 |

---

### Batch 1 — MVP（111 tools）

#### Group A1 — Objects 核心（7 资源）

> **YAML**：`openapi-specs/scm/config/sase/objects/objects-june.yaml`
> **base**：`https://api.strata.paloaltonetworks.com/config/objects/v1`

| Tool 名 | 方法 + 路径 | 类型 | operationId |
|---------|------------|------|-------------|
| `list_addresses` | GET `/addresses` | 只读 | ListAddresses |
| `get_address` | GET `/addresses/{id}` | 只读 | GetAddressesByID |
| `create_address` | POST `/addresses` | ⚠️ 写操作 | CreateAddresses |
| `update_address` | PUT `/addresses/{id}` | ⚠️ 写操作 | UpdateAddressesByID |
| `delete_address` | DELETE `/addresses/{id}` | ⚠️ 写操作 | DeleteAddressesByID |
| `list_address_groups` | GET `/address-groups` | 只读 | ListAddressGroups |
| `get_address_group` | GET `/address-groups/{id}` | 只读 | GetAddressGroupsByID |
| `create_address_group` | POST `/address-groups` | ⚠️ 写操作 | CreateAddressGroups |
| `update_address_group` | PUT `/address-groups/{id}` | ⚠️ 写操作 | UpdateAddressGroupsByID |
| `delete_address_group` | DELETE `/address-groups/{id}` | ⚠️ 写操作 | DeleteAddressGroupsByID |
| `list_services` | GET `/services` | 只读 | ListServices |
| `get_service` | GET `/services/{id}` | 只读 | GetServicesByID |
| `create_service` | POST `/services` | ⚠️ 写操作 | CreateServices |
| `update_service` | PUT `/services/{id}` | ⚠️ 写操作 | UpdateServicesByID |
| `delete_service` | DELETE `/services/{id}` | ⚠️ 写操作 | DeleteServicesByID |
| `list_service_groups` | GET `/service-groups` | 只读 | ListServiceGroups |
| `get_service_group` | GET `/service-groups/{id}` | 只读 | GetServiceGroupsByID |
| `create_service_group` | POST `/service-groups` | ⚠️ 写操作 | CreateServiceGroups |
| `update_service_group` | PUT `/service-groups/{id}` | ⚠️ 写操作 | UpdateServiceGroupsByID |
| `delete_service_group` | DELETE `/service-groups/{id}` | ⚠️ 写操作 | DeleteServiceGroupsByID |
| `list_tags` | GET `/tags` | 只读 | ListTags |
| `get_tag` | GET `/tags/{id}` | 只读 | GetTagsByID |
| `create_tag` | POST `/tags` | ⚠️ 写操作 | CreateTags |
| `update_tag` | PUT `/tags/{id}` | ⚠️ 写操作 | UpdateTagsByID |
| `delete_tag` | DELETE `/tags/{id}` | ⚠️ 写操作 | DeleteTagsByID |
| `list_application_groups` | GET `/application-groups` | 只读 | ListApplicationGroups |
| `get_application_group` | GET `/application-groups/{id}` | 只读 | GetApplicationGroupsByID |
| `create_application_group` | POST `/application-groups` | ⚠️ 写操作 | CreateApplicationGroups |
| `update_application_group` | PUT `/application-groups/{id}` | ⚠️ 写操作 | UpdateApplicationGroupsByID |
| `delete_application_group` | DELETE `/application-groups/{id}` | ⚠️ 写操作 | DeleteApplicationGroupsByID |
| `list_external_dynamic_lists` | GET `/external-dynamic-lists` | 只读 | ListExternalDynamicLists |
| `get_external_dynamic_list` | GET `/external-dynamic-lists/{id}` | 只读 | GetExternalDynamicListsByID |
| `create_external_dynamic_list` | POST `/external-dynamic-lists` | ⚠️ 写操作 | CreateExternalDynamicLists |
| `update_external_dynamic_list` | PUT `/external-dynamic-lists/{id}` | ⚠️ 写操作 | UpdateExternalDynamicListsByID |
| `delete_external_dynamic_list` | DELETE `/external-dynamic-lists/{id}` | ⚠️ 写操作 | DeleteExternalDynamicListsByID |

**A1 小计：35 tools**

---

#### Group B1 — Security 规则类（4 类含 move）

> **YAML**：`openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml`
> **base**：`https://api.strata.paloaltonetworks.com/config/security/v1`

| Tool 名 | 方法 + 路径 | 类型 | operationId |
|---------|------------|------|-------------|
| `list_security_rules` | GET `/security-rules` | 只读 | ListRules |
| `get_security_rule` | GET `/security-rules/{id}` | 只读 | GetSecurityRulesByID |
| `create_security_rule` | POST `/security-rules` | ⚠️ 写操作 | CreateSecurityRules |
| `update_security_rule` | PUT `/security-rules/{id}` | ⚠️ 写操作 | UpdateSecurityRulesByID |
| `delete_security_rule` | DELETE `/security-rules/{id}` | ⚠️ 写操作 | DeleteSecurityRulesByID |
| `move_security_rule` | POST `/security-rules/{id}:move` | ⚠️ 写操作 | MoveSecurityRulesByID |
| `list_decryption_rules` | GET `/decryption-rules` | 只读 | ListDecryptionRules |
| `get_decryption_rule` | GET `/decryption-rules/{id}` | 只读 | GetDecryptionRulesByID |
| `create_decryption_rule` | POST `/decryption-rules` | ⚠️ 写操作 | CreateDecryptionRules |
| `update_decryption_rule` | PUT `/decryption-rules/{id}` | ⚠️ 写操作 | UpdateDecryptionRulesByID |
| `delete_decryption_rule` | DELETE `/decryption-rules/{id}` | ⚠️ 写操作 | DeleteDecryptionRulesByID |
| `move_decryption_rule` | POST `/decryption-rules/{id}:move` | ⚠️ 写操作 | MoveDecryptionRulesByID |
| `list_app_override_rules` | GET `/app-override-rules` | 只读 | ListApplicationOverrideRules |
| `get_app_override_rule` | GET `/app-override-rules/{id}` | 只读 | GetApplicationOverrideRulesByID |
| `create_app_override_rule` | POST `/app-override-rules` | ⚠️ 写操作 | CreateApplicationOverrideRules |
| `update_app_override_rule` | PUT `/app-override-rules/{id}` | ⚠️ 写操作 | UpdateApplicationOverrideRulesByID |
| `delete_app_override_rule` | DELETE `/app-override-rules/{id}` | ⚠️ 写操作 | DeleteApplicationOverrideRulesByID |
| `move_app_override_rule` | POST `/app-override-rules/{id}:move` | ⚠️ 写操作 | MoveApplicationOverrideRulesByID |
| `list_dos_protection_rules` | GET `/dos-protection-rules` | 只读 | ListDoSProtectionRules |
| `get_dos_protection_rule` | GET `/dos-protection-rules/{id}` | 只读 | GetDoSProtectionRulesByID |
| `create_dos_protection_rule` | POST `/dos-protection-rules` | ⚠️ 写操作 | CreateDoSProtectionRules |
| `update_dos_protection_rule` | PUT `/dos-protection-rules/{id}` | ⚠️ 写操作 | UpdateDoSProtectionRulesByID |
| `delete_dos_protection_rule` | DELETE `/dos-protection-rules/{id}` | ⚠️ 写操作 | DeleteDoSProtectionRulesByID |

**B1 小计：23 tools**（dos-protection-rules YAML 无 `:move` 端点）

---

#### Group B2 — Security 档案只读（17 种档案）

> **YAML**：`openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml`
> **base**：`https://api.strata.paloaltonetworks.com/config/security/v1`
> Batch 1 仅纳入只读（list + get）；写操作在 Batch 2 Group B3 补齐。

| Tool 名 | 方法 + 路径 | 类型 | operationId |
|---------|------------|------|-------------|
| `list_anti_spyware_profiles` | GET `/anti-spyware-profiles` | 只读 | ListAntiSpywareProfiles |
| `get_anti_spyware_profile` | GET `/anti-spyware-profiles/{id}` | 只读 | GetAntiSpywareProfilesByID |
| `list_anti_spyware_signatures` | GET `/anti-spyware-signatures` | 只读 | ListAntiSpywareSignatures |
| `get_anti_spyware_signature` | GET `/anti-spyware-signatures/{id}` | 只读 | GetAntiSpywareSignaturesByID |
| `list_data_filtering_profiles` | GET `/data-filtering-profiles` | 只读 | ListDataFilteringProfiles |
| `get_data_filtering_profile` | GET `/data-filtering-profiles/{id}` | 只读 | GetDataFilteringProfilesByID |
| `list_data_objects` | GET `/data-objects` | 只读 | ListDataObjects |
| `get_data_object` | GET `/data-objects/{id}` | 只读 | GetDataObjectsByID |
| `list_decryption_exclusions` | GET `/decryption-exclusions` | 只读 | ListDecryptionExclusions |
| `get_decryption_exclusion` | GET `/decryption-exclusions/{id}` | 只读 | GetDecryptionExclusionsByID |
| `list_decryption_profiles` | GET `/decryption-profiles` | 只读 | ListDecryptionProfiles |
| `get_decryption_profile` | GET `/decryption-profiles/{id}` | 只读 | GetDecryptionProfilesByID |
| `list_dns_security_profiles` | GET `/dns-security-profiles` | 只读 | ListDNSSecurityProfiles |
| `get_dns_security_profile` | GET `/dns-security-profiles/{id}` | 只读 | GetDNSSecurityProfilesByID |
| `list_dos_protection_profiles` | GET `/dos-protection-profiles` | 只读 | ListDoSProtectionProfiles |
| `get_dos_protection_profile` | GET `/dos-protection-profiles/{id}` | 只读 | GetDoSProtectionProfilesByID |
| `list_file_blocking_profiles` | GET `/file-blocking-profiles` | 只读 | ListFileBlockingProfiles |
| `get_file_blocking_profile` | GET `/file-blocking-profiles/{id}` | 只读 | GetFileBlockingProfilesByID |
| `list_http_header_profiles` | GET `/http-header-profiles` | 只读 | ListHTTPHeaderProfiles |
| `get_http_header_profile` | GET `/http-header-profiles/{id}` | 只读 | GetHTTPHeaderProfilesByID |
| `list_profile_groups` | GET `/profile-groups` | 只读 | ListProfileGroups |
| `get_profile_group` | GET `/profile-groups/{id}` | 只读 | GetProfileGroupsByID |
| `list_url_access_profiles` | GET `/url-access-profiles` | 只读 | ListURLAccessProfiles |
| `get_url_access_profile` | GET `/url-access-profiles/{id}` | 只读 | GetURLAccessProfilesByID |
| `list_url_categories` | GET `/url-categories` | 只读 | ListURLCategories |
| `get_url_category` | GET `/url-categories/{id}` | 只读 | GetURLCategoriesByID |
| `list_url_filtering_categories` | GET `/url-filtering-categories` | 只读 | ListURLFilteringCategories |
| `list_vulnerability_protection_profiles` | GET `/vulnerability-protection-profiles` | 只读 | ListVulnerabilityProtectionProfiles |
| `get_vulnerability_protection_profile` | GET `/vulnerability-protection-profiles/{id}` | 只读 | GetVulnerabilityProtectionProfilesByID |
| `list_vulnerability_protection_signatures` | GET `/vulnerability-protection-signatures` | 只读 | ListVulnerabilityProtectionSignatures |
| `get_vulnerability_protection_signature` | GET `/vulnerability-protection-signatures/{id}` | 只读 | GetVulnerabilityProtectionSignaturesByID |
| `list_wildfire_anti_virus_profiles` | GET `/wildfire-anti-virus-profiles` | 只读 | ListWildFireAntiVirusProfiles |
| `get_wildfire_anti_virus_profile` | GET `/wildfire-anti-virus-profiles/{id}` | 只读 | GetWildFireAntiVirusProfilesByID |

**B2 小计：33 tools**（`url_filtering_categories` 仅有 list，无 `/{id}` 端点）

---

#### Group C1 — Operations（含写操作）

> **YAML**：`openapi-specs/scm/config/sase/operations/config-operations-march.yaml`
> **base**：`https://api.strata.paloaltonetworks.com/config/operations/v1`

| Tool 名 | 方法 + 路径 | 类型 | operationId |
|---------|------------|------|-------------|
| `list_jobs` | GET `/jobs` | 只读 | ListJobs |
| `get_job` | GET `/jobs/{id}` | 只读 | GetJobsByID |
| `list_config_versions` | GET `/config-versions` | 只读 | ListConfigVersions |
| `get_config_version` | GET `/config-versions/{version}` | 只读 | GetConfigVersionsByID |
| `get_running_config_version` | GET `/config-versions/running` | 只读 | GetRunningConfigVersions |
| `load_config_version` | POST `/config-versions:load` | ⚠️ 写操作 | LoadConfigVersions |
| `push_candidate_config` | POST `/config-versions/candidate:push` | ⚠️ 写操作 | PushCandidateConfigVersions |
| `delete_candidate_config` | DELETE `/config-versions/candidate` | ⚠️ 写操作 | DeleteCandidateConfigVersions |

**C1 小计：8 tools**

---

#### Group D1 — IAM（含写操作）

> **YAML**：`openapi-specs/scm/iam/ServiceAccounts.yaml`、`iam/Roles.yaml`、`iam/AccessPolicies.yaml`
> **base**：`https://api.sase.paloaltonetworks.com`

| Tool 名 | 方法 + 路径 | 类型 | operationId | YAML 来源 |
|---------|------------|------|-------------|-----------|
| `list_service_accounts` | GET `/iam/v1/service_accounts` | 只读 | get-iam-v1-service_accounts | ServiceAccounts.yaml |
| `get_service_account` | GET `/iam/v1/service_accounts/{id}` | 只读 | get-iam-v1-service_accounts-id | ServiceAccounts.yaml |
| `create_service_account` | POST `/iam/v1/service_accounts` | ⚠️ 写操作 | post-iam-v1-service_accounts | ServiceAccounts.yaml |
| `update_service_account` | PUT `/iam/v1/service_accounts/{id}` | ⚠️ 写操作 | put-iam-v1-service_accounts-id | ServiceAccounts.yaml |
| `delete_service_account` | DELETE `/iam/v1/service_accounts/{id}` | ⚠️ 写操作 | delete-iam-v1-service_accounts-id | ServiceAccounts.yaml |
| `reset_service_account_secret` | POST `/iam/v1/service_accounts/{id}/operations/reset` | ⚠️ 写操作 | post-iam-v1-service_accounts-id-operations-reset | ServiceAccounts.yaml |
| `list_roles` | GET `/iam/v1/roles` | 只读 | get-iam-v1-roles | Roles.yaml |
| `get_role` | GET `/iam/v1/roles/{name}` | 只读 | get-iam-v1-roles-name | Roles.yaml |
| `list_access_policies` | GET `/iam/v1/access_policies` | 只读 | get-iam-v1-access_policies | AccessPolicies.yaml |
| `get_access_policy` | GET `/iam/v1/access_policies/{id}` | 只读 | get-iam-v1-access_policies-id | AccessPolicies.yaml |
| `create_access_policy` | POST `/iam/v1/access_policies` | ⚠️ 写操作 | post-iam-v1-access_policies | AccessPolicies.yaml |
| `delete_access_policy` | DELETE `/iam/v1/access_policies/{id}` | ⚠️ 写操作 | delete-iam-v1-access_policies-id | AccessPolicies.yaml |

**D1 小计：12 tools**

---

### Batch 1 合计：35 + 23 + 33 + 8 + 12 = **111 tools**

---

### Batch 2 — 扩展（98 tools）

#### Group A2 — Objects 扩展（10 资源）

> **YAML**：`openapi-specs/scm/config/sase/objects/objects-june.yaml`
> **base**：`https://api.strata.paloaltonetworks.com/config/objects/v1`

| Tool 名 | 方法 + 路径 | 类型 |
|---------|------------|------|
| `list_applications` | GET `/applications` | 只读 |
| `get_application` | GET `/applications/{id}` | 只读 |
| `create_application` | POST `/applications` | ⚠️ 写操作 |
| `update_application` | PUT `/applications/{id}` | ⚠️ 写操作 |
| `delete_application` | DELETE `/applications/{id}` | ⚠️ 写操作 |
| `list_application_filters` | GET `/application-filters` | 只读 |
| `get_application_filter` | GET `/application-filters/{id}` | 只读 |
| `create_application_filter` | POST `/application-filters` | ⚠️ 写操作 |
| `update_application_filter` | PUT `/application-filters/{id}` | ⚠️ 写操作 |
| `delete_application_filter` | DELETE `/application-filters/{id}` | ⚠️ 写操作 |
| `list_schedules` | GET `/schedules` | 只读 |
| `get_schedule` | GET `/schedules/{id}` | 只读 |
| `create_schedule` | POST `/schedules` | ⚠️ 写操作 |
| `update_schedule` | PUT `/schedules/{id}` | ⚠️ 写操作 |
| `delete_schedule` | DELETE `/schedules/{id}` | ⚠️ 写操作 |
| `list_regions` | GET `/regions` | 只读 |
| `get_region` | GET `/regions/{id}` | 只读 |
| `create_region` | POST `/regions` | ⚠️ 写操作 |
| `update_region` | PUT `/regions/{id}` | ⚠️ 写操作 |
| `delete_region` | DELETE `/regions/{id}` | ⚠️ 写操作 |
| `list_hip_objects` | GET `/hip-objects` | 只读 |
| `get_hip_object` | GET `/hip-objects/{id}` | 只读 |
| `create_hip_object` | POST `/hip-objects` | ⚠️ 写操作 |
| `update_hip_object` | PUT `/hip-objects/{id}` | ⚠️ 写操作 |
| `delete_hip_object` | DELETE `/hip-objects/{id}` | ⚠️ 写操作 |
| `list_hip_profiles` | GET `/hip-profiles` | 只读 |
| `get_hip_profile` | GET `/hip-profiles/{id}` | 只读 |
| `create_hip_profile` | POST `/hip-profiles` | ⚠️ 写操作 |
| `update_hip_profile` | PUT `/hip-profiles/{id}` | ⚠️ 写操作 |
| `delete_hip_profile` | DELETE `/hip-profiles/{id}` | ⚠️ 写操作 |
| `list_log_forwarding_profiles` | GET `/log-forwarding-profiles` | 只读 |
| `get_log_forwarding_profile` | GET `/log-forwarding-profiles/{id}` | 只读 |
| `create_log_forwarding_profile` | POST `/log-forwarding-profiles` | ⚠️ 写操作 |
| `update_log_forwarding_profile` | PUT `/log-forwarding-profiles/{id}` | ⚠️ 写操作 |
| `delete_log_forwarding_profile` | DELETE `/log-forwarding-profiles/{id}` | ⚠️ 写操作 |
| `list_http_server_profiles` | GET `/http-server-profiles` | 只读 |
| `get_http_server_profile` | GET `/http-server-profiles/{id}` | 只读 |
| `create_http_server_profile` | POST `/http-server-profiles` | ⚠️ 写操作 |
| `update_http_server_profile` | PUT `/http-server-profiles/{id}` | ⚠️ 写操作 |
| `delete_http_server_profile` | DELETE `/http-server-profiles/{id}` | ⚠️ 写操作 |
| `list_syslog_server_profiles` | GET `/syslog-server-profiles` | 只读 |
| `get_syslog_server_profile` | GET `/syslog-server-profiles/{id}` | 只读 |
| `create_syslog_server_profile` | POST `/syslog-server-profiles` | ⚠️ 写操作 |
| `update_syslog_server_profile` | PUT `/syslog-server-profiles/{id}` | ⚠️ 写操作 |
| `delete_syslog_server_profile` | DELETE `/syslog-server-profiles/{id}` | ⚠️ 写操作 |
| `list_dynamic_user_groups` | GET `/dynamic-user-groups` | 只读 |
| `get_dynamic_user_group` | GET `/dynamic-user-groups/{id}` | 只读 |
| `create_dynamic_user_group` | POST `/dynamic-user-groups` | ⚠️ 写操作 |
| `update_dynamic_user_group` | PUT `/dynamic-user-groups/{id}` | ⚠️ 写操作 |
| `delete_dynamic_user_group` | DELETE `/dynamic-user-groups/{id}` | ⚠️ 写操作 |

**A2 小计：50 tools**

---

#### Group B3 — Security 档案写操作（16 种档案 × 3）

> **YAML**：`openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml`
> **base**：`https://api.strata.paloaltonetworks.com/config/security/v1`
> Batch 1 Group B2 已覆盖 list + get；本组补齐 create / update / delete。

| Tool 名 | 方法 + 路径 | 类型 |
|---------|------------|------|
| `create_anti_spyware_profile` | POST `/anti-spyware-profiles` | ⚠️ 写操作 |
| `update_anti_spyware_profile` | PUT `/anti-spyware-profiles/{id}` | ⚠️ 写操作 |
| `delete_anti_spyware_profile` | DELETE `/anti-spyware-profiles/{id}` | ⚠️ 写操作 |
| `create_anti_spyware_signature` | POST `/anti-spyware-signatures` | ⚠️ 写操作 |
| `update_anti_spyware_signature` | PUT `/anti-spyware-signatures/{id}` | ⚠️ 写操作 |
| `delete_anti_spyware_signature` | DELETE `/anti-spyware-signatures/{id}` | ⚠️ 写操作 |
| `create_data_filtering_profile` | POST `/data-filtering-profiles` | ⚠️ 写操作 |
| `update_data_filtering_profile` | PUT `/data-filtering-profiles/{id}` | ⚠️ 写操作 |
| `delete_data_filtering_profile` | DELETE `/data-filtering-profiles/{id}` | ⚠️ 写操作 |
| `create_data_object` | POST `/data-objects` | ⚠️ 写操作 |
| `update_data_object` | PUT `/data-objects/{id}` | ⚠️ 写操作 |
| `delete_data_object` | DELETE `/data-objects/{id}` | ⚠️ 写操作 |
| `create_decryption_exclusion` | POST `/decryption-exclusions` | ⚠️ 写操作 |
| `update_decryption_exclusion` | PUT `/decryption-exclusions/{id}` | ⚠️ 写操作 |
| `delete_decryption_exclusion` | DELETE `/decryption-exclusions/{id}` | ⚠️ 写操作 |
| `create_decryption_profile` | POST `/decryption-profiles` | ⚠️ 写操作 |
| `update_decryption_profile` | PUT `/decryption-profiles/{id}` | ⚠️ 写操作 |
| `delete_decryption_profile` | DELETE `/decryption-profiles/{id}` | ⚠️ 写操作 |
| `create_dns_security_profile` | POST `/dns-security-profiles` | ⚠️ 写操作 |
| `update_dns_security_profile` | PUT `/dns-security-profiles/{id}` | ⚠️ 写操作 |
| `delete_dns_security_profile` | DELETE `/dns-security-profiles/{id}` | ⚠️ 写操作 |
| `create_dos_protection_profile` | POST `/dos-protection-profiles` | ⚠️ 写操作 |
| `update_dos_protection_profile` | PUT `/dos-protection-profiles/{id}` | ⚠️ 写操作 |
| `delete_dos_protection_profile` | DELETE `/dos-protection-profiles/{id}` | ⚠️ 写操作 |
| `create_file_blocking_profile` | POST `/file-blocking-profiles` | ⚠️ 写操作 |
| `update_file_blocking_profile` | PUT `/file-blocking-profiles/{id}` | ⚠️ 写操作 |
| `delete_file_blocking_profile` | DELETE `/file-blocking-profiles/{id}` | ⚠️ 写操作 |
| `create_http_header_profile` | POST `/http-header-profiles` | ⚠️ 写操作 |
| `update_http_header_profile` | PUT `/http-header-profiles/{id}` | ⚠️ 写操作 |
| `delete_http_header_profile` | DELETE `/http-header-profiles/{id}` | ⚠️ 写操作 |
| `create_profile_group` | POST `/profile-groups` | ⚠️ 写操作 |
| `update_profile_group` | PUT `/profile-groups/{id}` | ⚠️ 写操作 |
| `delete_profile_group` | DELETE `/profile-groups/{id}` | ⚠️ 写操作 |
| `create_url_access_profile` | POST `/url-access-profiles` | ⚠️ 写操作 |
| `update_url_access_profile` | PUT `/url-access-profiles/{id}` | ⚠️ 写操作 |
| `delete_url_access_profile` | DELETE `/url-access-profiles/{id}` | ⚠️ 写操作 |
| `create_url_category` | POST `/url-categories` | ⚠️ 写操作 |
| `update_url_category` | PUT `/url-categories/{id}` | ⚠️ 写操作 |
| `delete_url_category` | DELETE `/url-categories/{id}` | ⚠️ 写操作 |
| `create_vulnerability_protection_profile` | POST `/vulnerability-protection-profiles` | ⚠️ 写操作 |
| `update_vulnerability_protection_profile` | PUT `/vulnerability-protection-profiles/{id}` | ⚠️ 写操作 |
| `delete_vulnerability_protection_profile` | DELETE `/vulnerability-protection-profiles/{id}` | ⚠️ 写操作 |
| `create_vulnerability_protection_signature` | POST `/vulnerability-protection-signatures` | ⚠️ 写操作 |
| `update_vulnerability_protection_signature` | PUT `/vulnerability-protection-signatures/{id}` | ⚠️ 写操作 |
| `delete_vulnerability_protection_signature` | DELETE `/vulnerability-protection-signatures/{id}` | ⚠️ 写操作 |
| `create_wildfire_anti_virus_profile` | POST `/wildfire-anti-virus-profiles` | ⚠️ 写操作 |
| `update_wildfire_anti_virus_profile` | PUT `/wildfire-anti-virus-profiles/{id}` | ⚠️ 写操作 |
| `delete_wildfire_anti_virus_profile` | DELETE `/wildfire-anti-virus-profiles/{id}` | ⚠️ 写操作 |

**B3 小计：48 tools**（`url_filtering_categories` 无写端点）

---

### Batch 2 合计：50 + 48 = **98 tools**

---

### 后续批次（待确认，~27 tools）

> 以下资源 API 模式非标准（无 `/{id}`、单例、批量操作），需单独评估后再纳入。

#### Group A3 — Objects 非标模式

| Tool 名（暂定） | 方法 + 路径 | 说明 |
|----------------|------------|------|
| `list_auto_tag_actions` | GET `/auto-tag-actions` | 无 GET by ID |
| `create_auto_tag_action` | POST `/auto-tag-actions` | ⚠️ 写操作 |
| `update_auto_tag_action` | PUT `/auto-tag-actions` | ⚠️ 写操作，无 ID 参数 |
| `delete_auto_tag_action` | DELETE `/auto-tag-actions` | ⚠️ 写操作，无 ID 参数 |
| `list_quarantined_devices` | GET `/quarantined-devices` | 无 GET/PUT by ID |
| `create_quarantined_device` | POST `/quarantined-devices` | ⚠️ 写操作 |
| `delete_quarantined_devices` | DELETE `/quarantined-devices` | ⚠️ 写操作，批量 |
| `list_device_context_segments` | GET `/device-context-segments` | 标准模式可提前升级 |
| `get_device_context_segment` | GET `/device-context-segments/{id}` | 标准模式 |
| `create_device_context_segment` | POST `/device-context-segments` | ⚠️ 写操作 |
| `update_device_context_segment` | PUT `/device-context-segments/{id}` | ⚠️ 写操作 |
| `delete_device_context_segment` | DELETE `/device-context-segments/{id}` | ⚠️ 写操作 |
| `list_advanced_device_objects` | GET `/advanced-device-objects` | 含 bulk PUT/DELETE |
| `get_advanced_device_object` | GET `/advanced-device-objects/{id}` | 标准模式 |
| `create_advanced_device_object` | POST `/advanced-device-objects` | ⚠️ 写操作 |
| `update_advanced_device_object` | PUT `/advanced-device-objects/{id}` | ⚠️ 写操作 |
| `delete_advanced_device_object` | DELETE `/advanced-device-objects/{id}` | ⚠️ 写操作 |

#### Group B4 — Security 特殊模式

| Tool 名（暂定） | 方法 + 路径 | 说明 |
|----------------|------------|------|
| `get_ssl_decryption_settings` | GET `/ssl-decryption-settings` | 单例，无 list/ID |
| `create_ssl_decryption_settings` | POST `/ssl-decryption-settings` | ⚠️ 写操作，单例 |
| `update_ssl_decryption_settings` | PUT `/ssl-decryption-settings` | ⚠️ 写操作，单例 |
| `delete_ssl_decryption_settings` | DELETE `/ssl-decryption-settings` | ⚠️ 写操作，单例 |
| `get_url_admin_override` | GET `/url-admin-override` | 无 GET by ID |
| `create_url_admin_override` | POST `/url-admin-override` | ⚠️ 写操作 |
| `delete_url_admin_override` | DELETE `/url-admin-override/{id}` | ⚠️ 写操作 |
| `get_saas_tenant_restrictions` | GET `/saas-tenant-restrictions` | 单例，只读 |
| `update_saas_tenant_restrictions` | PUT `/saas-tenant-restrictions` | ⚠️ 写操作，单例 |
| `list_url_filtering_categories` | GET `/url-filtering-categories` | 系统只读枚举（已在 B2 作为只读纳入）|

---

## 4. Auth 设计（内部，不暴露为 tool）

**YAML**：`openapi-specs/scm/auth/AuthService.yaml`

```
POST https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={SCM_CLIENT_ID}
&client_secret={SCM_CLIENT_SECRET}
&scope=tsg_id:{SCM_TSG_ID}
```

- 响应：`{ access_token, token_type, expires_in, scope }`
- 缓存策略：内存单例，`time.monotonic() + expires_in - 60` 后重新获取（默认 900 s TTL）
- `auth.py` 对外只暴露 `get_token() -> str` 和 `bearer_headers() -> dict`
- `threading.Lock` 保证并发安全

---

## 5. Error Mapping

| SCM HTTP 状态 | rest_client 返回 | server 层处理 |
|---|---|---|
| 2xx | `(status, body)` 正常 | 原样封装为 TextContent 返回 |
| 400 Bad Request | `(400, body)` | MCP error，含 SCM error detail |
| 401 Unauthorized | `(401, body)` | MCP error，文本含 "Authentication" |
| 403 Forbidden | `(403, body)` | MCP error，"Insufficient permissions" |
| 404 Not Found | `(404, body)` | MCP error，"Resource not found: {id}" |
| 409 Conflict | `(409, body)` | MCP error，含 SCM conflict detail |
| 5xx | `(5xx, body)` | MCP error，"SCM API error {status}: {detail}" |
| httpx timeout | `(0, {"error": "..."})` | MCP error，"Request timeout" |
| httpx connect error | `(0, {"error": "..."})` | MCP error，"Cannot connect to {base_url}" |
