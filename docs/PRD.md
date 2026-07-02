# PRD — scm-mcp-server 产品需求文档

**版本**：v0.1（MVP）
**状态**：草稿待确认
**关联文档**：[CLAUDE.md](../CLAUDE.md)（L1 工程契约）· [DESIGN.md](../DESIGN.md)（L2 技术设计）· [WORKFLOW.md](../WORKFLOW.md)（L3 阶段协议）

---

## 1. 目标用户与核心场景

### 1.1 网络安全工程师

**画像**：负责 Prisma Access / NGFW 策略日常维护，需要快速审查和变更安全规则，习惯 CLI 但需要自然语言辅助。

| 场景 | 用户输入示例 | 期待结果 |
|------|-------------|---------|
| 策略审查 | "列出 Shared 文件夹里所有 action 为 allow 且 destination 为 any 的规则" | 返回符合条件的规则列表，字段清晰可读 |
| 应急封堵 | "在 Shared/pre-rulebase 最顶部创建一条拒绝来自 1.2.3.0/24 的所有流量的规则" | 规则创建成功并确认位于 top |
| 对象盘点 | "哪些地址对象包含 192.168.1. 这个 IP 段，它们被哪些标签标记" | 地址列表含名称、IP、tag 字段 |

### 1.2 平台运维（NetOps）

**画像**：管理多个 folder 下的配置对象，关注对象一致性和命名规范，主要执行读操作和批量查询。

| 场景 | 用户输入示例 | 期待结果 |
|------|-------------|---------|
| 资产盘点 | "把 Branch-APAC 文件夹下所有服务对象列出来" | 完整服务对象列表，支持分页 |
| 命名审查 | "找出名字不包含 PROD_ 前缀的地址组" | 地址组列表，由 AI 在结果中过滤 |
| 配置核查 | "有没有叫 web-servers 的地址组，成员都有哪些" | 地址组详情含成员列表 |

### 1.3 安全架构师

**画像**：关注威胁态势，需要从告警数据中提炼风险摘要，推动优先级决策；偶尔审查策略结构。

| 场景 | 用户输入示例 | 期待结果 |
|------|-------------|---------|
| 告警态势 | "过去查出哪些 Critical 级别的未处理告警" | 告警列表含标题、严重级别、状态 |
| 告警下钻 | "给我看 incident ID INC-20240601-0042 的详情和修复建议" | 完整告警详情含 remediations 字段 |
| 策略风险 | "安全规则里有没有 disabled=true 但 action=allow 的规则" | 规则列表，由 AI 从结果中筛选 |

### 1.4 IAM 管理员

**画像**：管理 SCM 用户和权限，MVP 阶段不直接操作 IAM 资源，但使用本工具做**只读配置审计**，主要关切是凭据安全与权限最小化。

| 场景 | 用户输入示例 | 期待结果 |
|------|-------------|---------|
| 权限审计辅助 | "列出所有 tag 包含 'admin' 的地址对象" | 返回匹配列表（作为配置合规审计输入） |
| 凭据健康检查 | 工具启动时 / token 获取失败时 | 明确的错误信息，不泄露 secret 内容 |

---

## 2. MVP 功能边界

### 2.1 In Scope

| 能力域 | 能力描述 |
|--------|---------|
| **策略对象管理** | 对 SASE 配置面下的地址类、服务类、标签类对象具备完整的创建、读取、更新、删除能力 |
| **地址组读取** | 读取地址组列表及详情（地址组写操作在 v1.1 补齐） |
| **安全规则全生命周期** | 对 SASE 安全规则具备创建、读取、更新、删除及规则顺序调整能力 |
| **安全告警查询** | 对 SCM Incident 数据具备按条件搜索与按 ID 获取详情的能力 |
| **透明认证** | OAuth2 client_credentials 自动完成，token 内存缓存与到期刷新对用户完全透明 |
| **结构化错误反馈** | 所有 SCM API 错误、网络错误以可读文本通过 MCP error 返回，不崩溃 |

具体端点列表以 `openapi-specs/scm/` 下 YAML 为准，技术映射见 [DESIGN.md](../DESIGN.md)。

### 2.2 Out of Scope（MVP 不做）

| 项目 | 说明 |
|------|------|
| IAM 资源写操作 | 用户、角色、权限集、Service Account 的 CRUD；IAM 读操作列为 v1.1 候选 |
| 配置推送 / 部署 | commit、push-config、candidate 管理等部署操作不在本服务范围 |
| NGFW / CloudNGFW 专属配置面 | MVP 仅覆盖 SASE 配置面；NGFW 扩展列为 v1.2 候选 |
| 流量日志与策略命中分析 | 非 SCM Config API 范围 |
| 批量导入导出 | CSV / Terraform 互转等批处理能力 |
| 多租户动态切换 | 单 TSG_ID 绑定，运行时不支持切换租户 |
| Dry-run / 变更预览 | 写操作直接生效；预览模式列为 v1.1 待议 |
| Web UI 或 HTTP API | 传输层固定为 stdio MCP，不提供 REST 或 Web 界面 |

---

## 3. 产品级数据流

```
用户（自然语言）
      │
      ▼
AI 助手（Claude / Cursor）
  理解意图 → 选择 MCP tool → 组装参数
      │
      │  MCP stdio（JSON-RPC）
      ▼
scm-mcp-server
  ① token 管理（对用户透明）：
     - 内存中有效 token → 直接使用
     - 无 token 或临近到期 → 向 SCM auth 端点请求新 token，缓存
  ② 参数透传：
     - 将 AI 传入的结构化参数直接映射到 HTTP 请求
     - 不重写业务逻辑，不修改参数语义
  ③ 请求转发：
     - 向 SCM_BASE_URL 发起 HTTPS 请求，携带 Bearer token
      │
      │  HTTPS REST
      ▼
Strata Cloud Manager REST API
  执行业务逻辑，返回 JSON
      │
      ▼
scm-mcp-server
  ④ 响应处理：
     - 2xx：将 SCM JSON 原样封装为 MCP tool result 返回
     - 4xx / 5xx / 网络错误：转换为可读 MCP error（含状态码和 SCM 错误描述）
      │
      │  MCP stdio
      ▼
AI 助手
  将结果解释为自然语言回复给用户
```

**关键约束**（对用户可见的行为边界）：

- **写操作立即生效**：创建、更新、删除、规则移动调用成功后 SCM 即执行，无暂存或回滚窗口。
- **单租户绑定**：一个运行实例对应一个 TSG_ID，切换租户须重启并更换环境变量。
- **错误以文本返回**：任何失败都返回 MCP error，不挂起、不崩溃，AI 助手可将错误内容转述给用户。
- **凭据不经过 AI 助手**：token 在 server 进程内部管理，从不出现在 MCP 消息中。

---

## 4. 验收标准

### AC-AUTH — 认证与启动

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-AUTH-1 | 缺少任意必填环境变量（`SCM_CLIENT_ID` / `SCM_CLIENT_SECRET` / `SCM_TSG_ID`）时，server 启动后打印含缺失变量名的错误信息并退出，退出码非 0 | 本地删除环境变量后运行 `python -m scm_mcp_server`，检查 stderr 和退出码 |
| AC-AUTH-2 | 首次 tool 调用触发 token 请求，从发起请求到收到有效 token 的耗时不超过 5 秒（网络正常条件下） | 查看 server 日志时间戳或 httpx 请求计时 |
| AC-AUTH-3 | 同一 token 有效期内的第二次 tool 调用不产生新的 `/auth/v1/oauth2/access_token` HTTP 请求 | `tests/test_auth.py` 中 mock 断言：第二次调用 `get_token()` 时 httpx post 调用次数仍为 1 |

### AC-OBJ — 对象管理

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-OBJ-1 | `scm_list_addresses` 返回的每个元素包含 `id`、`name`、`folder`（或 `snippet` / `device`）三个字段 | 集成测试：对含对象的 folder 调用，检查响应结构 |
| AC-OBJ-2 | 通过 `scm_create_address` 创建的对象，用 `scm_get_address(id=<返回的 id>)` 能取回，且 `name` 和地址字段值与创建时一致 | 集成测试：create → get 比对 |
| AC-OBJ-3 | `scm_get_address` 传入不存在的 ID 时，MCP 返回 error，error 文本包含 "not found"（大小写不敏感），不返回空对象 | 单元测试：mock 404 响应，断言 error 文本 |

### AC-SEC — 安全规则

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-SEC-1 | `scm_move_security_rule(destination="top")` 执行后，`scm_list_security_rules` 返回的第一条规则 ID 等于被移动规则的 ID | 集成测试：move → list，比对 `data[0].id` |
| AC-SEC-2 | `scm_create_security_rule` 创建的规则，`action` 字段值等于请求时传入的字符串（`allow`/`deny`/`drop` 等），不被 server 转换或修改 | 集成测试：create → get，比对 `action` 字段 |

### AC-INC — 告警查询

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-INC-1 | `scm_search_incidents` 返回结构中 `header.dataCount` 为整数，`data` 为数组（可为空数组） | 集成测试或 mock 测试：断言响应类型 |
| AC-INC-2 | `scm_get_incident` 返回对象包含 `incident_id`、`title`、`severity_id` 三个字段且均非 null | 集成测试：对已知存在的 incident_id 调用，检查字段 |

### AC-ERR — 错误处理

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-ERR-1 | SCM 返回 401 时，MCP error 文本包含 "Authentication"（大小写不敏感） | 单元测试：mock 401 响应，断言 error 文本 |
| AC-ERR-2 | `SCM_BASE_URL` 指向不可达地址时，任意 tool 调用在 15 秒内返回 MCP error，不挂起 | 本地测试：将 BASE_URL 改为 `https://10.255.255.1`，调用 list，计时 |

### AC-REG — 工具注册

| ID | 标准 | 验证方式 |
|----|------|---------|
| AC-REG-1 | `mcp dev scm_mcp_server/server.py` 启动后，MCP Inspector 展示的 tool 数量与 [DESIGN.md](../DESIGN.md) 中 MCP Tool 清单定义的数量完全一致 | 人工：Inspector → Tools 页面，核对数量 |

---

## 5. 风险与待确认问题

### R1 — 凭据安全

**描述**：`SCM_CLIENT_ID` / `SCM_CLIENT_SECRET` 以明文存在于 `.env` 文件或 shell 环境中；若意外提交或进程被 dump，凭据会暴露。

**缓解措施**：
- `.env` 加入 `.gitignore`，CI 配置显式阻止含 `SECRET` 的文件
- server 日志不得输出任何凭据或 token 内容（日志中出现的 Authorization header 需脱敏）
- token 生命周期结束后立即从内存清除（不做持久化）

**待确认**：
- 生产部署是否需要对接外部 Secret Manager（如 AWS Secrets Manager、Vault）？如是，需在 `auth.py` 增加抽象层。
- SCM Service Account 是否支持 IP 白名单绑定，以缩小凭据滥用面？

---

### R2 — 写操作防误触

**描述**：AI 助手理解偏差或用户表述模糊时，可能触发 create / update / delete / move 等不可回滚操作。SCM 无原生变更暂存机制，操作立即生效。

**缓解措施**：
- 所有写操作的 tool description 标注 `⚠️ 写操作，立即生效，不可通过本工具回滚`
- DESIGN.md 中写操作 tool 与读操作 tool 分离命名（`scm_create_*` vs `scm_list_*`），便于 AI 助手区分意图

**待确认**：
- 是否需要在 server 层实现 `SCM_READONLY=true` 模式（接收写操作 tool 调用但返回 error，不实际发送）？
- 是否需要在 tool 调用前向 AI 助手返回"即将执行写操作，请确认"的二次确认流程？（需要 MCP SDK 支持）

---

### R3 — Token 权限边界

**描述**：OAuth2 client_credentials 的 Service Account 若权限过宽（如 super-admin），本工具暴露后等同于向 AI 助手开放全租户写权限。

**缓解措施**：
- README 明确建议创建**最小权限** Service Account，仅授予所需资源的读写权限
- DESIGN.md 和 README 文档化每类 tool 所需的 SCM IAM 权限

**待确认**：
- SCM IAM 是否支持 **folder 级** 权限粒度（即 Service Account 只能操作特定 folder）？
- SCM IAM 是否支持**只读角色**的精确绑定，用于需要 audit-only 场景的 IAM 管理员？

---

### R4 — API 版本漂移

**描述**：`openapi-specs/scm/` 下的 YAML 来自 `pan.dev` 仓库，若上游更新（新增/删除字段、端点路径变更）而本地软链未更新，会导致 tool inputSchema 与实际 API 静默不一致，产生难以排查的错误。

**缓解措施**：
- `openapi-specs` 以软链形式绑定到 `pan.dev` 仓库的**固定 commit hash**，不 track 浮动分支
- 建议在 CI 中添加校验：当 `openapi-specs/` 下 YAML 文件内容哈希变化时，触发 `tests/test_tools.py` 全量回归

**待确认**：
- `pan.dev` 仓库是否有 breaking change 通知机制（release notes / changelog）？
- 是否需要在本仓库 CI 中定期同步并运行 schema diff 检测？

---

### R5 — 并发 token 刷新竞争

**描述**：多个 MCP tool 并发调用时，若 token 恰好在同一时刻到期，可能触发多次并发的 token 刷新请求，产生不必要的 API 调用，极端情况下若 SCM 有 rate limit 会导致所有刷新失败。

**缓解措施**：
- `auth.py` 使用 `asyncio.Lock` 保证同一时刻只有一个协程执行 token 刷新，其余协程等待并复用结果
- 此为实现阶段的**前置条件**，在 Phase 1 完成前必须验证（见 WORKFLOW.md Phase 1 测试要求）

**待确认**：
- SCM Auth 端点是否有 rate limit 文档？如有，阈值是多少？
