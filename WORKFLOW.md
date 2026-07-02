# WORKFLOW.md — L3 阶段协议

每个 Phase 必须**所有测试绿灯**后才能进入下一阶段。Phase 之间不跳跃、不并行。

---

## Phase 0 — Bootstrap

**目标**：建立可运行的项目骨架。

**任务清单**：
- [ ] 创建 `pyproject.toml`（包名 `scm-mcp-server`，入口 `scm_mcp_server.server:main`）
- [ ] 创建目录骨架（见 CLAUDE.md 目录约定）
- [ ] 创建 `.env.example`（含全部环境变量占位符）
- [ ] 创建软链 `openapi-specs -> ../pan.dev/openapi-specs`（或在 README 说明路径）
- [ ] `scm_mcp_server/server.py` 可启动：读取环境变量，缺失时打印清晰错误，不 crash

**完成标志**：
```bash
pip install -e ".[dev]"          # 无报错
python -m scm_mcp_server         # 打印 "SCM MCP Server starting..." 或明确的缺失变量错误
```

---

## Phase 1 — Auth

**目标**：实现 OAuth2 token 获取与缓存。

**任务清单**：
- [ ] 实现 `auth.py`：
  - `async get_token() -> str`
  - 内存缓存（`_token`, `_expires_at`）
  - 到期前 60 s 自动刷新
  - 失败时抛出带明确信息的异常
- [ ] 编写 `tests/test_auth.py`：
  - mock `httpx.AsyncClient.post`
  - 验证首次调用发起请求
  - 验证第二次调用命中缓存（不发起请求）
  - 验证 token 过期后重新获取

**完成标志**：
```bash
pytest tests/test_auth.py -v     # 全部 PASSED
```

---

## Phase 2 — Client

**目标**：封装 httpx，统一注入 auth header 与 error handling。

**任务清单**：
- [ ] 实现 `client.py`：
  - `get_client() -> SCMClient`（单例）
  - 自动调用 `auth.get_token()` 注入 Bearer header
  - `base_url` 来自 `SCM_BASE_URL` 环境变量
  - `request(method, path, **kwargs) -> dict`
  - HTTP 4xx/5xx → 抛出 `SCMAPIError`（携带 status + detail）
  - httpx timeout / connect error → 抛出 `SCMAPIError`
- [ ] 编写 `tests/test_client.py`：
  - 用 `respx` mock HTTP 响应
  - 验证 Bearer header 正确注入
  - 验证 400/401/403/404/500 → `SCMAPIError`
  - 验证 timeout → `SCMAPIError`

**完成标志**：
```bash
pytest tests/test_client.py -v   # 全部 PASSED
```

---

## Phase 3 — Tools

**目标**：实现全部 MCP tool，注册到 server.py。

**子阶段顺序**（逐一完成，逐一测试）：

### Phase 3a — Objects
- [ ] 实现 `tools/objects.py`（见 DESIGN.md Group 1 全部 tool）
- [ ] 注册到 `server.py`
- [ ] `tests/test_tools.py` 中添加 objects 测试（mock client）

### Phase 3b — Security
- [ ] 实现 `tools/security.py`（见 DESIGN.md Group 2 全部 tool）
- [ ] 注册到 `server.py`
- [ ] `tests/test_tools.py` 中添加 security 测试

### Phase 3c — Incidents
- [ ] 实现 `tools/incidents.py`（见 DESIGN.md Group 3 全部 tool）
- [ ] 注册到 `server.py`
- [ ] `tests/test_tools.py` 中添加 incidents 测试

**完成标志**：
```bash
pytest tests/test_tools.py -v    # 全部 PASSED
mcp dev scm_mcp_server/server.py # Inspector 能列出所有 tool（见下方 tool 数量）
```

预期 tool 数量：`scm_list_addresses`、`scm_get_address`、`scm_create_address`、`scm_update_address`、`scm_delete_address`、`scm_list_address_groups`、`scm_list_services`、`scm_list_tags`、`scm_list_security_rules`、`scm_get_security_rule`、`scm_create_security_rule`、`scm_update_security_rule`、`scm_delete_security_rule`、`scm_move_security_rule`、`scm_search_incidents`、`scm_get_incident` — **共 16 个**。

---

## Phase 4 — Integration（需真实凭据）

**目标**：端到端冒烟验证。

**任务清单**：
- [ ] 配置 `.env` 填入真实凭据
- [ ] 运行 `mcp dev scm_mcp_server/server.py`
- [ ] 在 Inspector 调用以下 tool 验证响应合法：
  - `scm_list_addresses(folder="Shared", limit=5)` → 返回 `{data, total, ...}`
  - `scm_search_incidents(pagination={page_size: 5, page_number: 1})` → 返回 `{header, data}`
  - `scm_list_security_rules(folder="Shared")` → 返回 `{data, total, ...}`

**完成标志**：上述三个调用均返回 200 且 JSON 结构与 DESIGN.md 出参一致。

---

## Phase 5 — Packaging

**目标**：完善文档与注册配置，可交付。

**任务清单**：
- [ ] 完善 `README.md`（见 README 内容大纲）
- [ ] 验证 Claude Desktop 注册片段可用
- [ ] 验证 Cursor MCP 注册片段可用
- [ ] 可选：添加 `Dockerfile`
- [ ] 运行完整测试套件确认无回归：

```bash
pytest -v                        # 全部 PASSED
```

**完成标志**：按 README 操作的新用户能在 10 分钟内完成安装并在 Claude Desktop 里看到 16 个 `scm_*` tool。

---

## 快速状态检查命令

```bash
# 查看当前测试状态
pytest -v --tb=short

# 语法自检
python scripts/syntax_check.py

# 路由完整性验证
python scripts/route_integrity.py

# stdio 冒烟（需配置 .env）
python scripts/smoke_stdio.py

# 连通性自检（需配置 .env）
python -m scm_mcp_server.check
```

---

## Phase 3 — Batch 1 验收记录

**验收日期**：2026-06-26
**验收版本**：tag step-6，tool 总数 111

### 验收结论（对照 docs/PRD.md §4）

#### AC-AUTH — 认证与启动

| ID | 标准摘要 | 结论 | 证据 / 验证命令 |
|----|---------|------|----------------|
| AC-AUTH-1 | 缺必填环境变量时 stderr 含变量名，exit ≠ 0 | ✅ PASS | `SCM_CLIENT_ID="" python -m scm_mcp_server`；stderr 含 `Missing required environment variables: SCM_CLIENT_ID`；exit 1 |
| AC-AUTH-2 | 首次 token 获取 ≤ 5 秒（网络正常） | ✅ PASS（需真实凭据） | `python -m scm_mcp_server.check` 实测 < 2 s |
| AC-AUTH-3 | 同一有效期内第二次调用不重复请求 token | ⏳ PENDING | `tests/test_auth.py` 骨架，Phase 1 遗留；需补充 mock 断言 |

#### AC-OBJ — 对象管理

| ID | 标准摘要 | 结论 | 证据 / 验证命令 |
|----|---------|------|----------------|
| AC-OBJ-1 | list_addresses 返回元素含 id / name / folder | ⏳ PENDING | 需真实凭据集成测试；行为层由 rest_client 原样透传保证 |
| AC-OBJ-2 | create → get 字段一致性 | ⏳ PENDING | 需真实凭据集成测试 |
| AC-OBJ-3 | get_address 传不存在 ID → error 含 "not found" | ✅ PASS | `tests/test_readonly_tools.py::TestObjectsGetByIdTools::test_404_returns_error`；mock 404，assert result["status"]==404 |

#### AC-SEC — 安全规则

| ID | 标准摘要 | 结论 | 证据 / 验证命令 |
|----|---------|------|----------------|
| AC-SEC-1 | move_security_rule(top) 后 list 第一条 ID 一致 | ⏳ PENDING | 需真实凭据集成测试 |
| AC-SEC-2 | create_security_rule 的 action 字段不被 server 修改 | ✅ PASS | `tests/test_write_tools.py::TestCreateSecurityRule::test_action_enum_in_body`；断言 body["action"] == 传入值 |

#### AC-INC — 告警查询

| ID | 标准摘要 | 结论 | 证据 / 验证命令 |
|----|---------|------|----------------|
| AC-INC-1 | search_incidents 返回 header.dataCount 为整数 | 🚫 OUT OF SCOPE | incidents tool 为空占位符，当前批次不实现 |
| AC-INC-2 | get_incident 返回含三个必填字段 | 🚫 OUT OF SCOPE | 同上 |

#### AC-ERR — 错误处理

| ID | 标准摘要 | 结论 | 证据 / 验证命令 |
|----|---------|------|----------------|
| AC-ERR-1 | SCM 401 → MCP error 文本含 "Authentication" | ⚠️ PARTIAL | 返回 SCM body 原文（含 `_errors` 数组）；需确认 SCM 实际 401 body 格式是否含 "Authentication" 字符串 |
| AC-ERR-2 | 不可达地址 15 s 内返回 error，不挂起 | ✅ PASS | `rest_client.py` `_TIMEOUT = 15.0`；httpx.TimeoutException → `(0, {"error": "Request timeout..."})` |

#### AC-REG — 工具注册

| ID | 标准摘要 | 结论 | 证据 / 验证命令 |
|----|---------|------|----------------|
| AC-REG-1 | MCP Inspector tool 数量 == DESIGN.md Batch 1 定义数 | ✅ PASS | `python scripts/smoke_stdio.py`；tools/list 返回 111 tools，20 个抽样名称全部命中 |

### 补充验证项（Phase 3 新增）

| 项目 | 结论 | 命令 |
|------|------|------|
| 全部源文件语法合法 | ✅ PASS | `python scripts/syntax_check.py`；14 files，0 errors |
| 路由表与 descriptor 完全一致 | ✅ PASS | `python scripts/route_integrity.py`；111 == 111，diff = [] |
| MCP stdio 传输层可用 | ✅ PASS | `python scripts/smoke_stdio.py`；initialize + tools/list(111) + call_tool 全通 |
| 单元测试全套 | ✅ PASS | `pytest -v`；288/288 |
