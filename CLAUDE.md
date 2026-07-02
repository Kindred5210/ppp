# CLAUDE.md — L1 工程契约

## 项目身份

**scm-mcp-server**：通过 MCP stdio 接口将 Palo Alto Networks Strata Cloud Manager (SCM) REST API 暴露给 AI 助手的 Python 服务。

服务只做参数透传与协议适配，不重写任何 SCM 业务逻辑。

---

## 技术栈（禁止替换）

| 组件 | 指定版本/库 | 禁止替换为 |
|------|------------|-----------|
| 语言 | Python 3.11+ | — |
| MCP SDK | `mcp`（官方，`pip install mcp`） | 任何第三方 MCP 封装 |
| HTTP 客户端 | `httpx`（异步） | requests、aiohttp 等 |
| 传输层 | stdio | SSE、HTTP、WebSocket |
| 依赖管理 | `pyproject.toml` | setup.py、requirements.txt 作为主文件 |

---

## 目录约定

```
scm_mcp_server/
  __init__.py
  server.py          # MCP server 入口；注册所有 tool，启动 stdio loop
  auth.py            # OAuth2 client_credentials token 获取与内存缓存
  client.py          # httpx AsyncClient 封装；统一 Bearer header、base_url、error mapping
  tools/
    __init__.py
    objects.py       # 地址/地址组/服务/服务组/标签等对象 CRUD
    security.py      # 安全策略规则 CRUD + move
    incidents.py     # 告警搜索与详情查询
    deployment.py    # 部署状态查询（预留）
openapi-specs -> ../pan.dev/openapi-specs  # 软链，只读；禁止修改其中任何文件
tests/
  test_auth.py
  test_client.py
  test_tools.py
pyproject.toml
.env.example
CLAUDE.md
DESIGN.md
WORKFLOW.md
README.md
docs/
  PRD.md             # 产品需求文档（目标用户、MVP 边界、验收标准、风险）
```

---

## 环境变量（凭据唯一来源）

| 变量 | 说明 | 是否必填 |
|------|------|---------|
| `SCM_CLIENT_ID` | OAuth2 Client ID | 必填 |
| `SCM_CLIENT_SECRET` | OAuth2 Client Secret | 必填 |
| `SCM_TSG_ID` | Tenant Service Group ID | 必填 |
| `SCM_BASE_URL` | API 基址 | 选填，默认 `https://api.strata.paloaltonetworks.com` |

---

## 禁止事项

1. **禁止硬编码**任何凭据、URL、tenant ID。
2. **禁止手抄或臆造 schema**；所有 tool 的 `inputSchema` / 出参字段必须来自 `openapi-specs/scm/` 下对应 YAML 文件的 `parameters` 或 `requestBody`。
3. **禁止重写业务逻辑**；server 只透传参数，由 SCM REST API 执行逻辑。
4. **禁止切换传输层**；始终保持 stdio。
5. **禁止修改** `openapi-specs/` 目录下任何文件。
6. **禁止**将 Auth 端点（`/auth/v1/oauth2/access_token`）暴露为 MCP tool；token 管理在 `auth.py` 内部完成。

---

## 必须执行

- 每个 tool 的 `inputSchema` 注释须标注来源 YAML 路径，格式：
  ```python
  # ref: openapi-specs/scm/config/sase/objects/objects-june.yaml#/components/schemas/Address
  ```
- `auth.py` 必须实现 token 内存缓存，依据 `expires_in` 在到期前自动刷新（建议提前 60 秒）。
- HTTP 4xx / 5xx 统一在 `client.py` 捕获，转为 MCP `error` 返回，不允许 unhandled exception 穿透到 MCP layer。
- 每个 Phase 完成后必须所有测试绿灯才能进入下一 Phase（见 WORKFLOW.md）。
- 新增 tool 时同步更新 DESIGN.md 的 tool 列表。
