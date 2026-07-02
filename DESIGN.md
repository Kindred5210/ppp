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

### 3.1 提取与排除规则

- 每个 `(path, method)` 映射为一个 MCP tool，命名使用 `{动作}_{资源}` 的小写下划线形式。
- `GET` 端点标记为只读；`POST` / `PUT` / `PATCH` / `DELETE` 端点标记为 `⚠️ 写操作`。
- `POST ...:move` 类端点单独命名为 `move_{资源}`。
- Auth OAuth2 端点只供 `auth.py` 内部使用，不暴露为 MCP tool：
  - `openapi-specs/scm/auth/AuthService.yaml#/paths/~1auth~1v1~1oauth2~1access_token/post`
  - `openapi-specs/scm/auth/AuthService.yaml#/paths/~1auth~1v1~1oauth2~1userinfo/post`
  - `openapi-specs/scm/auth/AuthService.yaml#/paths/~1auth~1v1~1oauth2~1userinfo/get`
- SASE deployment、mobile agent、network infrastructure，以及本节列为后续候选的非标准对象 / 安全单例端点，不进入 Batch 1 / Batch 2。

### 3.2 实现批次说明

| 批次 | 内容 | Tool 数 | 状态 |
|---|---|---:|---|
| **Batch 1** | Objects 核心 + Security 规则 + Security 档案只读 + Operations 全部 + IAM 全部 | **111** | MVP |
| **Batch 2** | Objects 扩展 + Security 档案写操作 | **98** | 扩展 |
| **后续候选** | 非标准对象、批量/路径型操作、安全单例/特殊设置 | **29** | 待单独评估 |

---

### 3.3 Batch 1 — MVP（111 tools）

#### Group A1 — Objects 核心（35 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_addresses` | GET `/addresses` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses/get` |
| `get_address` | GET `/addresses/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses~1{id}/get` |
| `create_address` | POST `/addresses` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses/post` |
| `update_address` | PUT `/addresses/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses~1{id}/put` |
| `delete_address` | DELETE `/addresses/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1addresses~1{id}/delete` |
| `list_address_groups` | GET `/address-groups` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups/get` |
| `get_address_group` | GET `/address-groups/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups~1{id}/get` |
| `create_address_group` | POST `/address-groups` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups/post` |
| `update_address_group` | PUT `/address-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups~1{id}/put` |
| `delete_address_group` | DELETE `/address-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1address-groups~1{id}/delete` |
| `list_services` | GET `/services` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services/get` |
| `get_service` | GET `/services/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services~1{id}/get` |
| `create_service` | POST `/services` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services/post` |
| `update_service` | PUT `/services/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services~1{id}/put` |
| `delete_service` | DELETE `/services/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1services~1{id}/delete` |
| `list_service_groups` | GET `/service-groups` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups/get` |
| `get_service_group` | GET `/service-groups/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups~1{id}/get` |
| `create_service_group` | POST `/service-groups` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups/post` |
| `update_service_group` | PUT `/service-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups~1{id}/put` |
| `delete_service_group` | DELETE `/service-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1service-groups~1{id}/delete` |
| `list_tags` | GET `/tags` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags/get` |
| `get_tag` | GET `/tags/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags~1{id}/get` |
| `create_tag` | POST `/tags` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags/post` |
| `update_tag` | PUT `/tags/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags~1{id}/put` |
| `delete_tag` | DELETE `/tags/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1tags~1{id}/delete` |
| `list_application_groups` | GET `/application-groups` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups/get` |
| `get_application_group` | GET `/application-groups/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups~1{id}/get` |
| `create_application_group` | POST `/application-groups` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups/post` |
| `update_application_group` | PUT `/application-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups~1{id}/put` |
| `delete_application_group` | DELETE `/application-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-groups~1{id}/delete` |
| `list_external_dynamic_lists` | GET `/external-dynamic-lists` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists/get` |
| `get_external_dynamic_list` | GET `/external-dynamic-lists/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists~1{id}/get` |
| `create_external_dynamic_list` | POST `/external-dynamic-lists` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists/post` |
| `update_external_dynamic_list` | PUT `/external-dynamic-lists/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists~1{id}/put` |
| `delete_external_dynamic_list` | DELETE `/external-dynamic-lists/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1external-dynamic-lists~1{id}/delete` |

#### Group B1 — Security 规则类（23 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_security_rules` | GET `/security-rules` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules/get` |
| `get_security_rule` | GET `/security-rules/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules~1{id}/get` |
| `create_security_rule` | POST `/security-rules` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules/post` |
| `update_security_rule` | PUT `/security-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules~1{id}/put` |
| `delete_security_rule` | DELETE `/security-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules~1{id}/delete` |
| `move_security_rule` | POST `/security-rules/{id}:move` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1security-rules~1{id}:move/post` |
| `list_decryption_rules` | GET `/decryption-rules` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules/get` |
| `get_decryption_rule` | GET `/decryption-rules/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules~1{id}/get` |
| `create_decryption_rule` | POST `/decryption-rules` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules/post` |
| `update_decryption_rule` | PUT `/decryption-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules~1{id}/put` |
| `delete_decryption_rule` | DELETE `/decryption-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules~1{id}/delete` |
| `move_decryption_rule` | POST `/decryption-rules/{id}:move` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-rules~1{id}:move/post` |
| `list_app_override_rules` | GET `/app-override-rules` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules/get` |
| `get_app_override_rule` | GET `/app-override-rules/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules~1{id}/get` |
| `create_app_override_rule` | POST `/app-override-rules` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules/post` |
| `update_app_override_rule` | PUT `/app-override-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules~1{id}/put` |
| `delete_app_override_rule` | DELETE `/app-override-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules~1{id}/delete` |
| `move_app_override_rule` | POST `/app-override-rules/{id}:move` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1app-override-rules~1{id}:move/post` |
| `list_dos_protection_rules` | GET `/dos-protection-rules` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules/get` |
| `get_dos_protection_rule` | GET `/dos-protection-rules/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules~1{id}/get` |
| `create_dos_protection_rule` | POST `/dos-protection-rules` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules/post` |
| `update_dos_protection_rule` | PUT `/dos-protection-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules~1{id}/put` |
| `delete_dos_protection_rule` | DELETE `/dos-protection-rules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-rules~1{id}/delete` |

> `dos-protection-rules` 在当前 YAML 中无 `:move` 端点。

#### Group B2 — Security 档案只读（33 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_anti_spyware_profiles` | GET `/anti-spyware-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles/get` |
| `get_anti_spyware_profile` | GET `/anti-spyware-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles~1{id}/get` |
| `list_anti_spyware_signatures` | GET `/anti-spyware-signatures` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures/get` |
| `get_anti_spyware_signature` | GET `/anti-spyware-signatures/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures~1{id}/get` |
| `list_data_filtering_profiles` | GET `/data-filtering-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles/get` |
| `get_data_filtering_profile` | GET `/data-filtering-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles~1{id}/get` |
| `list_data_objects` | GET `/data-objects` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects/get` |
| `get_data_object` | GET `/data-objects/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects~1{id}/get` |
| `list_decryption_exclusions` | GET `/decryption-exclusions` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions/get` |
| `get_decryption_exclusion` | GET `/decryption-exclusions/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions~1{id}/get` |
| `list_decryption_profiles` | GET `/decryption-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles/get` |
| `get_decryption_profile` | GET `/decryption-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles~1{id}/get` |
| `list_dns_security_profiles` | GET `/dns-security-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles/get` |
| `get_dns_security_profile` | GET `/dns-security-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles~1{id}/get` |
| `list_dos_protection_profiles` | GET `/dos-protection-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles/get` |
| `get_dos_protection_profile` | GET `/dos-protection-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles~1{id}/get` |
| `list_file_blocking_profiles` | GET `/file-blocking-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles/get` |
| `get_file_blocking_profile` | GET `/file-blocking-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles~1{id}/get` |
| `list_http_header_profiles` | GET `/http-header-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles/get` |
| `get_http_header_profile` | GET `/http-header-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles~1{id}/get` |
| `list_profile_groups` | GET `/profile-groups` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups/get` |
| `get_profile_group` | GET `/profile-groups/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups~1{id}/get` |
| `list_url_access_profiles` | GET `/url-access-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles/get` |
| `get_url_access_profile` | GET `/url-access-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles~1{id}/get` |
| `list_url_categories` | GET `/url-categories` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories/get` |
| `get_url_category` | GET `/url-categories/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories~1{id}/get` |
| `list_url_filtering_categories` | GET `/url-filtering-categories` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-filtering-categories/get` |
| `list_vulnerability_protection_profiles` | GET `/vulnerability-protection-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles/get` |
| `get_vulnerability_protection_profile` | GET `/vulnerability-protection-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles~1{id}/get` |
| `list_vulnerability_protection_signatures` | GET `/vulnerability-protection-signatures` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures/get` |
| `get_vulnerability_protection_signature` | GET `/vulnerability-protection-signatures/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures~1{id}/get` |
| `list_wildfire_anti_virus_profiles` | GET `/wildfire-anti-virus-profiles` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles/get` |
| `get_wildfire_anti_virus_profile` | GET `/wildfire-anti-virus-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles~1{id}/get` |

> `url-filtering-categories` 在当前 YAML 中仅有 list 端点，无 `/{id}` 端点。

#### Group C1 — Operations（8 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_jobs` | GET `/jobs` | 只读 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1jobs/get` |
| `get_job` | GET `/jobs/{id}` | 只读 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1jobs~1{id}/get` |
| `list_config_versions` | GET `/config-versions` | 只读 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions/get` |
| `get_config_version` | GET `/config-versions/{version}` | 只读 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions~1{version}/get` |
| `get_running_config_version` | GET `/config-versions/running` | 只读 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions~1running/get` |
| `load_config_version` | POST `/config-versions:load` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions:load/post` |
| `push_candidate_config` | POST `/config-versions/candidate:push` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions~1candidate:push/post` |
| `delete_candidate_config` | DELETE `/config-versions/candidate` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/operations/config-operations-march.yaml#/paths/~1config-versions~1candidate/delete` |

#### Group D1 — IAM（12 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_service_accounts` | GET `/iam/v1/service_accounts` | 只读 | `openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts/get` |
| `get_service_account` | GET `/iam/v1/service_accounts/{id}` | 只读 | `openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts~1{id}/get` |
| `create_service_account` | POST `/iam/v1/service_accounts` | ⚠️ 写操作 | `openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts/post` |
| `update_service_account` | PUT `/iam/v1/service_accounts/{id}` | ⚠️ 写操作 | `openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts~1{id}/put` |
| `delete_service_account` | DELETE `/iam/v1/service_accounts/{id}` | ⚠️ 写操作 | `openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts~1{id}/delete` |
| `reset_service_account_secret` | POST `/iam/v1/service_accounts/{id}/operations/reset` | ⚠️ 写操作 | `openapi-specs/scm/iam/ServiceAccounts.yaml#/paths/~1iam~1v1~1service_accounts~1{id}~1operations~1reset/post` |
| `list_roles` | GET `/iam/v1/roles` | 只读 | `openapi-specs/scm/iam/Roles.yaml#/paths/~1iam~1v1~1roles/get` |
| `get_role` | GET `/iam/v1/roles/{name}` | 只读 | `openapi-specs/scm/iam/Roles.yaml#/paths/~1iam~1v1~1roles~1{name}/get` |
| `list_access_policies` | GET `/iam/v1/access_policies` | 只读 | `openapi-specs/scm/iam/AccessPolicies.yaml#/paths/~1iam~1v1~1access_policies/get` |
| `get_access_policy` | GET `/iam/v1/access_policies/{id}` | 只读 | `openapi-specs/scm/iam/AccessPolicies.yaml#/paths/~1iam~1v1~1access_policies~1{id}/get` |
| `create_access_policy` | POST `/iam/v1/access_policies` | ⚠️ 写操作 | `openapi-specs/scm/iam/AccessPolicies.yaml#/paths/~1iam~1v1~1access_policies/post` |
| `delete_access_policy` | DELETE `/iam/v1/access_policies/{id}` | ⚠️ 写操作 | `openapi-specs/scm/iam/AccessPolicies.yaml#/paths/~1iam~1v1~1access_policies~1{id}/delete` |

**Batch 1 合计：35 + 23 + 33 + 8 + 12 = 111 tools**

---

### 3.4 Batch 2 — 扩展（98 tools）

#### Group A2 — Objects 扩展（50 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_applications` | GET `/applications` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1applications/get` |
| `get_application` | GET `/applications/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1applications~1{id}/get` |
| `create_application` | POST `/applications` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1applications/post` |
| `update_application` | PUT `/applications/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1applications~1{id}/put` |
| `delete_application` | DELETE `/applications/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1applications~1{id}/delete` |
| `list_application_filters` | GET `/application-filters` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-filters/get` |
| `get_application_filter` | GET `/application-filters/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-filters~1{id}/get` |
| `create_application_filter` | POST `/application-filters` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-filters/post` |
| `update_application_filter` | PUT `/application-filters/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-filters~1{id}/put` |
| `delete_application_filter` | DELETE `/application-filters/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1application-filters~1{id}/delete` |
| `list_schedules` | GET `/schedules` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1schedules/get` |
| `get_schedule` | GET `/schedules/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1schedules~1{id}/get` |
| `create_schedule` | POST `/schedules` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1schedules/post` |
| `update_schedule` | PUT `/schedules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1schedules~1{id}/put` |
| `delete_schedule` | DELETE `/schedules/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1schedules~1{id}/delete` |
| `list_regions` | GET `/regions` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1regions/get` |
| `get_region` | GET `/regions/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1regions~1{id}/get` |
| `create_region` | POST `/regions` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1regions/post` |
| `update_region` | PUT `/regions/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1regions~1{id}/put` |
| `delete_region` | DELETE `/regions/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1regions~1{id}/delete` |
| `list_hip_objects` | GET `/hip-objects` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-objects/get` |
| `get_hip_object` | GET `/hip-objects/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-objects~1{id}/get` |
| `create_hip_object` | POST `/hip-objects` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-objects/post` |
| `update_hip_object` | PUT `/hip-objects/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-objects~1{id}/put` |
| `delete_hip_object` | DELETE `/hip-objects/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-objects~1{id}/delete` |
| `list_hip_profiles` | GET `/hip-profiles` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-profiles/get` |
| `get_hip_profile` | GET `/hip-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-profiles~1{id}/get` |
| `create_hip_profile` | POST `/hip-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-profiles/post` |
| `update_hip_profile` | PUT `/hip-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-profiles~1{id}/put` |
| `delete_hip_profile` | DELETE `/hip-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1hip-profiles~1{id}/delete` |
| `list_log_forwarding_profiles` | GET `/log-forwarding-profiles` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1log-forwarding-profiles/get` |
| `get_log_forwarding_profile` | GET `/log-forwarding-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1log-forwarding-profiles~1{id}/get` |
| `create_log_forwarding_profile` | POST `/log-forwarding-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1log-forwarding-profiles/post` |
| `update_log_forwarding_profile` | PUT `/log-forwarding-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1log-forwarding-profiles~1{id}/put` |
| `delete_log_forwarding_profile` | DELETE `/log-forwarding-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1log-forwarding-profiles~1{id}/delete` |
| `list_http_server_profiles` | GET `/http-server-profiles` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1http-server-profiles/get` |
| `get_http_server_profile` | GET `/http-server-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1http-server-profiles~1{id}/get` |
| `create_http_server_profile` | POST `/http-server-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1http-server-profiles/post` |
| `update_http_server_profile` | PUT `/http-server-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1http-server-profiles~1{id}/put` |
| `delete_http_server_profile` | DELETE `/http-server-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1http-server-profiles~1{id}/delete` |
| `list_syslog_server_profiles` | GET `/syslog-server-profiles` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1syslog-server-profiles/get` |
| `get_syslog_server_profile` | GET `/syslog-server-profiles/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1syslog-server-profiles~1{id}/get` |
| `create_syslog_server_profile` | POST `/syslog-server-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1syslog-server-profiles/post` |
| `update_syslog_server_profile` | PUT `/syslog-server-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1syslog-server-profiles~1{id}/put` |
| `delete_syslog_server_profile` | DELETE `/syslog-server-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1syslog-server-profiles~1{id}/delete` |
| `list_dynamic_user_groups` | GET `/dynamic-user-groups` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1dynamic-user-groups/get` |
| `get_dynamic_user_group` | GET `/dynamic-user-groups/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1dynamic-user-groups~1{id}/get` |
| `create_dynamic_user_group` | POST `/dynamic-user-groups` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1dynamic-user-groups/post` |
| `update_dynamic_user_group` | PUT `/dynamic-user-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1dynamic-user-groups~1{id}/put` |
| `delete_dynamic_user_group` | DELETE `/dynamic-user-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1dynamic-user-groups~1{id}/delete` |

#### Group B3 — Security 档案写操作（48 tools）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `create_anti_spyware_profile` | POST `/anti-spyware-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles/post` |
| `update_anti_spyware_profile` | PUT `/anti-spyware-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles~1{id}/put` |
| `delete_anti_spyware_profile` | DELETE `/anti-spyware-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-profiles~1{id}/delete` |
| `create_anti_spyware_signature` | POST `/anti-spyware-signatures` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures/post` |
| `update_anti_spyware_signature` | PUT `/anti-spyware-signatures/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures~1{id}/put` |
| `delete_anti_spyware_signature` | DELETE `/anti-spyware-signatures/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1anti-spyware-signatures~1{id}/delete` |
| `create_data_filtering_profile` | POST `/data-filtering-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles/post` |
| `update_data_filtering_profile` | PUT `/data-filtering-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles~1{id}/put` |
| `delete_data_filtering_profile` | DELETE `/data-filtering-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-filtering-profiles~1{id}/delete` |
| `create_data_object` | POST `/data-objects` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects/post` |
| `update_data_object` | PUT `/data-objects/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects~1{id}/put` |
| `delete_data_object` | DELETE `/data-objects/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1data-objects~1{id}/delete` |
| `create_decryption_exclusion` | POST `/decryption-exclusions` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions/post` |
| `update_decryption_exclusion` | PUT `/decryption-exclusions/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions~1{id}/put` |
| `delete_decryption_exclusion` | DELETE `/decryption-exclusions/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-exclusions~1{id}/delete` |
| `create_decryption_profile` | POST `/decryption-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles/post` |
| `update_decryption_profile` | PUT `/decryption-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles~1{id}/put` |
| `delete_decryption_profile` | DELETE `/decryption-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1decryption-profiles~1{id}/delete` |
| `create_dns_security_profile` | POST `/dns-security-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles/post` |
| `update_dns_security_profile` | PUT `/dns-security-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles~1{id}/put` |
| `delete_dns_security_profile` | DELETE `/dns-security-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dns-security-profiles~1{id}/delete` |
| `create_dos_protection_profile` | POST `/dos-protection-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles/post` |
| `update_dos_protection_profile` | PUT `/dos-protection-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles~1{id}/put` |
| `delete_dos_protection_profile` | DELETE `/dos-protection-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1dos-protection-profiles~1{id}/delete` |
| `create_file_blocking_profile` | POST `/file-blocking-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles/post` |
| `update_file_blocking_profile` | PUT `/file-blocking-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles~1{id}/put` |
| `delete_file_blocking_profile` | DELETE `/file-blocking-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1file-blocking-profiles~1{id}/delete` |
| `create_http_header_profile` | POST `/http-header-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles/post` |
| `update_http_header_profile` | PUT `/http-header-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles~1{id}/put` |
| `delete_http_header_profile` | DELETE `/http-header-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1http-header-profiles~1{id}/delete` |
| `create_profile_group` | POST `/profile-groups` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups/post` |
| `update_profile_group` | PUT `/profile-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups~1{id}/put` |
| `delete_profile_group` | DELETE `/profile-groups/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1profile-groups~1{id}/delete` |
| `create_url_access_profile` | POST `/url-access-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles/post` |
| `update_url_access_profile` | PUT `/url-access-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles~1{id}/put` |
| `delete_url_access_profile` | DELETE `/url-access-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-access-profiles~1{id}/delete` |
| `create_url_category` | POST `/url-categories` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories/post` |
| `update_url_category` | PUT `/url-categories/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories~1{id}/put` |
| `delete_url_category` | DELETE `/url-categories/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-categories~1{id}/delete` |
| `create_vulnerability_protection_profile` | POST `/vulnerability-protection-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles/post` |
| `update_vulnerability_protection_profile` | PUT `/vulnerability-protection-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles~1{id}/put` |
| `delete_vulnerability_protection_profile` | DELETE `/vulnerability-protection-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-profiles~1{id}/delete` |
| `create_vulnerability_protection_signature` | POST `/vulnerability-protection-signatures` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures/post` |
| `update_vulnerability_protection_signature` | PUT `/vulnerability-protection-signatures/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures~1{id}/put` |
| `delete_vulnerability_protection_signature` | DELETE `/vulnerability-protection-signatures/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1vulnerability-protection-signatures~1{id}/delete` |
| `create_wildfire_anti_virus_profile` | POST `/wildfire-anti-virus-profiles` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles/post` |
| `update_wildfire_anti_virus_profile` | PUT `/wildfire-anti-virus-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles~1{id}/put` |
| `delete_wildfire_anti_virus_profile` | DELETE `/wildfire-anti-virus-profiles/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1wildfire-anti-virus-profiles~1{id}/delete` |

> Batch 1 已覆盖这些 Security 档案的只读端点；Batch 2 仅补齐写操作。`url-filtering-categories` 无写端点。

**Batch 2 合计：50 + 48 = 98 tools**

---

### 3.5 后续候选（29 endpoints，暂不进入 Batch 1 / Batch 2）

以下端点来自指定 YAML，但因 API 模式为非标准对象、批量/路径型操作、单例或特殊设置，需单独评估 tool 命名、幂等性和防误触策略后再纳入。

#### Group A3 — Objects 非标准 / 批量 / 路径型操作（20 endpoints）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `list_advanced_device_objects` | GET `/advanced-device-objects` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects/get` |
| `create_advanced_device_object` | POST `/advanced-device-objects` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects/post` |
| `update_advanced_device_objects_by_path` | PUT `/advanced-device-objects` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects/put` |
| `delete_advanced_device_objects_by_names` | DELETE `/advanced-device-objects` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects/delete` |
| `get_advanced_device_object` | GET `/advanced-device-objects/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects~1{id}/get` |
| `update_advanced_device_object` | PUT `/advanced-device-objects/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects~1{id}/put` |
| `delete_advanced_device_object` | DELETE `/advanced-device-objects/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1advanced-device-objects~1{id}/delete` |
| `list_auto_tag_actions` | GET `/auto-tag-actions` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1auto-tag-actions/get` |
| `create_auto_tag_action` | POST `/auto-tag-actions` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1auto-tag-actions/post` |
| `update_auto_tag_action` | PUT `/auto-tag-actions` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1auto-tag-actions/put` |
| `delete_auto_tag_action` | DELETE `/auto-tag-actions` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1auto-tag-actions/delete` |
| `list_device_context_segments` | GET `/device-context-segments` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1device-context-segments/get` |
| `create_device_context_segment` | POST `/device-context-segments` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1device-context-segments/post` |
| `delete_device_context_segments_by_name` | DELETE `/device-context-segments` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1device-context-segments/delete` |
| `get_device_context_segment` | GET `/device-context-segments/{id}` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1device-context-segments~1{id}/get` |
| `update_device_context_segment` | PUT `/device-context-segments/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1device-context-segments~1{id}/put` |
| `delete_device_context_segment` | DELETE `/device-context-segments/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1device-context-segments~1{id}/delete` |
| `list_quarantined_devices` | GET `/quarantined-devices` | 只读 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1quarantined-devices/get` |
| `create_quarantined_device` | POST `/quarantined-devices` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1quarantined-devices/post` |
| `delete_quarantined_devices` | DELETE `/quarantined-devices` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/objects/objects-june.yaml#/paths/~1quarantined-devices/delete` |

#### Group B4 — Security 单例 / 特殊设置（9 endpoints）

| Tool 名 | 方法 + 路径 | 类型 | OpenAPI YAML 引用位置 |
|---|---|---|---|
| `get_ssl_decryption_settings` | GET `/ssl-decryption-settings` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1ssl-decryption-settings/get` |
| `create_ssl_decryption_settings` | POST `/ssl-decryption-settings` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1ssl-decryption-settings/post` |
| `update_ssl_decryption_settings` | PUT `/ssl-decryption-settings` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1ssl-decryption-settings/put` |
| `delete_ssl_decryption_settings` | DELETE `/ssl-decryption-settings` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1ssl-decryption-settings/delete` |
| `get_url_admin_override` | GET `/url-admin-override` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-admin-override/get` |
| `create_url_admin_override` | POST `/url-admin-override` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-admin-override/post` |
| `delete_url_admin_override` | DELETE `/url-admin-override/{id}` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1url-admin-override~1{id}/delete` |
| `get_saas_tenant_restrictions` | GET `/saas-tenant-restrictions` | 只读 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1saas-tenant-restrictions/get` |
| `update_saas_tenant_restrictions` | PUT `/saas-tenant-restrictions` | ⚠️ 写操作 | `openapi-specs/scm/config/sase/security/security-services-R2-2026.yaml#/paths/~1saas-tenant-restrictions/put` |

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
