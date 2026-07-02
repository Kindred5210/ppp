# scm-mcp-server

Palo Alto Networks Strata Cloud Manager (SCM) 的 MCP server，通过 stdio 将 SCM REST API 暴露给 Claude、Cursor 等 AI 助手。

**当前版本**：Batch 1 MVP，共 **111 个 MCP tool**，覆盖对象管理、安全规则、安全配置文件、运维操作、IAM 五个域。

---

## Prerequisites

- Python 3.11+
- SCM 租户凭据：Client ID、Client Secret、TSG ID
  （SCM 控制台 → Identity → Service Accounts 创建）

---

## Install

```bash
git clone <this-repo>
cd scm-mcp-server
pip install -e ".[dev]"
```

---

## 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入真实凭据
```

`.env` 内容：

```
SCM_CLIENT_ID=your-client-id
SCM_CLIENT_SECRET=your-client-secret
SCM_TSG_ID=your-tsg-id
SCM_BASE_URL=https://api.strata.paloaltonetworks.com   # 可选，此为默认值
```

---

## 连通性自检

配置凭据后先跑自检，验证 token 获取和 SCM API 可达：

```bash
python -m scm_mcp_server.check
```

预期输出：

```
[check] OK   token obtained (first 8 chars: eyJ0eXAi...)
[check] OK   GET /config/operations/v1/jobs → HTTP 200
[check] All checks passed.
```

---

## 运行

```bash
# 直接运行（stdio 模式，供 MCP 客户端连接）
python -m scm_mcp_server

# 用 MCP Inspector 调试
mcp dev scm_mcp_server/server.py
```

---

## 在 Claude Desktop 注册

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "scm": {
      "command": "python",
      "args": ["-m", "scm_mcp_server"],
      "cwd": "/absolute/path/to/scm-mcp-server",
      "env": {
        "SCM_CLIENT_ID": "your-client-id",
        "SCM_CLIENT_SECRET": "your-client-secret",
        "SCM_TSG_ID": "your-tsg-id"
      }
    }
  }
}
```

重启 Claude Desktop，在对话中询问 "列出可用工具" 确认 `list_addresses` 等工具已加载。

---

## 在 Cursor 注册

创建或编辑 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "scm": {
      "command": "python",
      "args": ["-m", "scm_mcp_server"],
      "cwd": "/absolute/path/to/scm-mcp-server",
      "env": {
        "SCM_CLIENT_ID": "your-client-id",
        "SCM_CLIENT_SECRET": "your-client-secret",
        "SCM_TSG_ID": "your-tsg-id"
      }
    }
  }
}
```

重启 Cursor，在 Composer 中输入 `@scm` 确认工具可用。

---

## 可用 Tool 列表（共 111 个，Batch 1 MVP）

> 标注 ⚠️ 的 tool 为写操作，**立即生效，不可通过本工具回滚**。

### Objects Core — 地址 / 服务 / 标签 / 应用组 / EDL（35 个）

| 操作 | 资源 |
|------|------|
| list / get | addresses, address_groups, services, service_groups, tags, application_groups, external_dynamic_lists |
| ⚠️ create / update / delete | 同上 7 类资源 |

### Security Rules — 安全 / 解密 / 应用覆盖 / DoS 规则（23 个）

| 操作 | 资源 |
|------|------|
| list / get | security_rules, decryption_rules, app_override_rules, dos_protection_rules |
| ⚠️ create / update / delete | 同上 4 类规则 |
| ⚠️ move | security_rules, decryption_rules, app_override_rules（调整规则顺序） |

### Security Profiles — 安全配置文件（33 个，只读）

list / get 操作，涵盖：

anti_spyware_profiles, anti_spyware_signatures, data_filtering_profiles, data_objects, decryption_exclusions, decryption_profiles, dns_security_profiles, dos_protection_profiles, file_blocking_profiles, http_header_profiles, profile_groups, url_access_profiles, url_categories, url_filtering_categories（仅 list）, vulnerability_protection_profiles, vulnerability_protection_signatures, wildfire_anti_virus_profiles

### Operations — 配置版本与任务（8 个）

| 操作 | 工具 |
|------|------|
| 只读 | list_jobs, get_job, list_config_versions, get_config_version, get_running_config_version |
| ⚠️ 写 | load_config_version（加载版本）, push_candidate_config（**高风险**：下发到真实设备）, delete_candidate_config |

### IAM — 身份与访问管理（12 个）

| 操作 | 资源 |
|------|------|
| list / get | service_accounts, roles, access_policies |
| ⚠️ create / update / delete | service_accounts |
| ⚠️ create / delete | access_policies |
| ⚠️ reset | reset_service_account_secret（重置 secret） |

完整入参/出参映射见 [DESIGN.md](DESIGN.md)。

---

## 开发与测试

```bash
# 运行全部单元测试
pytest -v

# 语法自检（AST parse 全部 .py）
python scripts/syntax_check.py

# 路由完整性验证（路由表 key == descriptor 名称集合）
python scripts/route_integrity.py

# stdio 冒烟（需配置 .env 凭据）
python scripts/smoke_stdio.py
```

---

## OpenAPI 规范

tool 的 schema 来源为 `../pan.dev/openapi-specs/scm/`（相对本仓库父目录）：

```
openapi-specs/scm/
  auth/AuthService.yaml
  config/
    sase/objects/objects-june.yaml
    sase/security/security-services-R2-2026.yaml
    sase/operations/config-operations-march.yaml
  iam/
    ServiceAccounts.yaml  Roles.yaml  AccessPolicies.yaml
```

**禁止修改规范文件**；如需更新请从上游 `pan.dev` 仓库同步。
