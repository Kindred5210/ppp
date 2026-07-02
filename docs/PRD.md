# PRD — scm-mcp-server 产品需求文档

**版本**：v0.1（MVP）
**状态**：草稿待确认
**L1 约束来源**：[CLAUDE.md](../CLAUDE.md)
**技术映射来源**：[DESIGN.md](../DESIGN.md)
**阶段执行来源**：[WORKFLOW.md](../WORKFLOW.md)

---

## 1. 目标用户与核心场景

### 1.1 网络安全工程师

**用户画像**：负责 SCM 中安全策略、对象和安全配置的日常维护，需要在 AI 助手内用自然语言完成查询、核查和受控变更。

| 核心场景 | 用户目标 | 产品行为 |
|---|---|---|
| 策略审查 | 按 folder、rulebase、名称、标签、动作等条件定位安全策略 | AI 助手调用对应 MCP tool，返回 SCM 原始结果中的关键字段，并说明查询是否成功 |
| 策略变更 | 创建、更新、删除或调整安全规则顺序 | MCP server 将结构化参数转发给 SCM REST API；写操作成功或失败均返回可观察结果 |
| 对象维护 | 查询或维护地址、地址组、服务、服务组、标签等核心对象 | 用户可通过自然语言触发对象读取和变更，字段含义以 SCM 返回为准 |
| 变更核验 | 变更后确认资源是否存在、字段是否符合预期 | 用户可再次查询同一资源，比较返回字段与变更请求 |

### 1.2 平台运维

**用户画像**：维护多 folder、多配置版本和平台运行状态，关注配置一致性、任务状态、版本可见性和运维操作风险。

| 核心场景 | 用户目标 | 产品行为 |
|---|---|---|
| 配置盘点 | 列出指定范围内的对象、规则、安全配置文件或 IAM 资源 | 返回 SCM 查询结果，分页、过滤和字段约束以对应 OpenAPI YAML 为准 |
| 任务追踪 | 查看配置任务、版本状态或运行版本信息 | 通过 MCP tool 获取 SCM Operations 结果，返回任务或版本状态 |
| 配置版本操作 | 在明确请求下执行版本加载、候选配置处理等运维写操作 | 写操作仅在用户明确表达操作意图时触发；结果由 SCM REST API 决定 |
| 运行故障定位 | 识别认证失败、权限不足、网络错误或 SCM API 错误 | 返回结构化 MCP error，错误文本包含可定位的状态或原因 |

### 1.3 安全架构师

**用户画像**：负责策略架构、控制面覆盖度和安全能力治理，需要快速理解 SCM 配置状态，但不希望工具替代架构判断。

| 核心场景 | 用户目标 | 产品行为 |
|---|---|---|
| 策略结构评估 | 查看规则、对象和安全配置文件的覆盖情况 | 返回可供 AI 助手汇总的 SCM 配置数据 |
| 风险线索识别 | 查找过宽规则、未使用对象、缺少安全配置文件关联等线索 | MCP server 只返回 SCM 数据；AI 助手可基于返回结果做解释，但 server 不内置安全判断逻辑 |
| 变更影响分析 | 在变更前后对比相关对象或规则 | 用户通过多次读取结果进行对比；MVP 不提供独立 diff 引擎 |
| 治理文档输入 | 将查询结果转化为评审材料或整改清单 | AI 助手负责归纳表达；server 不生成报告模板 |

### 1.4 IAM 管理员

**用户画像**：管理 SCM 身份、角色和访问策略，关注 Service Account 最小权限、凭据安全和写权限边界。

| 核心场景 | 用户目标 | 产品行为 |
|---|---|---|
| IAM 资源盘点 | 查看 Service Account、角色和访问策略 | 返回 SCM IAM API 结果，具体资源字段以 OpenAPI YAML 为准 |
| IAM 变更 | 在授权场景下创建、更新或删除 IAM 相关资源 | 仅在用户明确请求写操作时触发；SCM 权限不足时返回 403 类错误 |
| 凭据健康检查 | 判断本地凭据是否存在、是否能换取 token、是否具备目标权限 | 缺失环境变量、认证失败和权限不足均返回可验证错误，不暴露 secret 或 access token |
| 权限边界验证 | 使用低权限 token 验证只读或受限行为 | server 不提权、不切换凭据、不绕过 SCM IAM 控制 |

---

## 2. MVP 功能边界

MVP 是一个 **MCP stdio 到 SCM REST API 的协议适配层**。它不重写 SCM 业务逻辑，不维护 SCM 资源状态，不在本地实现策略判断。

具体端点清单、请求参数、响应字段和 tool 到 REST 的技术映射以 `openapi-specs/scm/` 下 YAML 与 [DESIGN.md](../DESIGN.md) 为准。本文件只描述产品能力边界，不列举、不臆造 REST 端点。

### 2.1 In Scope

| 能力域 | MVP 能力描述 |
|---|---|
| MCP 接入 | 通过 stdio 暴露 SCM 能力，供 Claude、Cursor 等 MCP 客户端调用 |
| 透明认证 | 使用环境变量中的 SCM Client ID、Client Secret、TSG ID 获取 OAuth2 token，并在进程内缓存和刷新 |
| 配置对象管理 | 支持对 MVP 覆盖的 SCM 配置对象进行查询和受控写操作；对象字段与约束来自 OpenAPI YAML |
| 安全规则管理 | 支持安全规则类资源的查询、创建、更新、删除和顺序调整；具体资源集合以 DESIGN.md 的 MVP 批次为准 |
| 安全配置审计 | 支持读取 MVP 覆盖的安全配置文件和相关资源，作为策略评审和架构治理输入 |
| 运维状态与配置版本 | 支持查询 SCM 任务、配置版本和运行版本，并在明确请求下执行 MVP 覆盖的配置版本写操作 |
| IAM 管理 | 支持 MVP 覆盖的 Service Account、角色和访问策略读取，以及授权范围内的 IAM 写操作 |
| 错误映射 | 将 SCM 4xx、5xx、网络错误、认证错误转换为 MCP error；不让未处理异常穿透到 MCP layer |
| Schema 溯源 | 每个 tool 的输入结构必须能追溯到 `openapi-specs/scm/` 中对应 YAML，不允许手写或猜测字段 |

### 2.2 Out of Scope

| 不做事项 | 边界说明 |
|---|---|
| REST 端点清单维护 | PRD 不维护端点列表；端点、operationId、参数和响应字段属于 OpenAPI YAML 与 DESIGN.md |
| SCM 业务逻辑重写 | 不在 server 中实现策略优化、风险评分、对象解析、自动补全或跨资源推理 |
| 自动化安全决策 | 不自动判断规则是否安全、不自动生成推荐策略、不自动执行整改 |
| 持久化数据仓库 | 不缓存 SCM 资源数据，不提供历史趋势、审计报表或本地索引 |
| 多租户运行时切换 | 单个进程绑定一个 TSG ID；切换租户需要更换环境变量并重启 |
| 非 stdio 传输 | 不提供 HTTP、SSE、WebSocket 或 Web UI |
| 批量导入导出 | 不提供 CSV、Terraform、Panorama 配置迁移或批处理编排 |
| 未纳入 DESIGN.md MVP 批次的能力 | 即使 OpenAPI YAML 中存在相关资源，未进入 DESIGN.md MVP 批次的能力不属于本阶段交付 |
| 凭据托管系统 | MVP 只从环境变量读取凭据，不内置 Vault、云 Secret Manager 或 KMS 集成 |

---

## 3. 产品级数据流

1. 用户在 AI 助手中用自然语言提出查询或变更请求。
2. AI 助手根据 MCP tool 描述选择一个或多个 tool，并组装结构化参数。
3. MCP 客户端通过 stdio 将 tool 调用发送给 `scm-mcp-server`。
4. `scm-mcp-server` 在进程内检查 token 状态；无有效 token 时使用环境变量中的凭据向 SCM 认证服务换取 token。
5. `scm-mcp-server` 将参数透传给 SCM REST API；不改写字段含义，不补造 SCM 业务参数。
6. SCM REST API 执行业务逻辑、权限校验和数据变更，并返回 JSON 结果或错误。
7. `scm-mcp-server` 将成功结果封装为 MCP tool result，将失败结果封装为 MCP error。
8. AI 助手把 MCP 返回内容解释给用户，并在需要时提示用户继续查询或确认下一步操作。

产品级链路为：**用户 → AI 助手 / MCP 客户端 → MCP stdio → scm-mcp-server → SCM REST API → scm-mcp-server → MCP 结果 → 用户**。

技术性的 tool 与 REST 端点映射不在本节重画；详见 [DESIGN.md](../DESIGN.md)。

---

## 4. 验收标准

| ID | 验收标准 | 验证方式 |
|---|---|---|
| AC-1 | `docs/PRD.md` 不列举 REST 端点路径；端点与 tool 映射只引用 `openapi-specs/scm/` 和 `DESIGN.md` | 在 PRD 中搜索 REST path 形态；确认无端点清单 |
| AC-2 | MCP Inspector 中展示的 MVP tool 集合与 `DESIGN.md` MVP 批次定义一致 | 启动 MCP Inspector，导出 tool 名称集合，与 DESIGN.md 中 MVP tool 清单比对 |
| AC-3 | 任一 tool 的 input schema 均可追溯到 `openapi-specs/scm/` 下对应 YAML | 抽样检查 tool descriptor 注释或 schema 生成来源；字段不存在于 YAML 时验收失败 |
| AC-4 | 缺少任一必填环境变量时，server 退出码非 0，stderr 包含缺失变量名 | 移除单个必填环境变量后启动 server，记录退出码和 stderr |
| AC-5 | 默认日志和 MCP 返回内容中不包含 `SCM_CLIENT_SECRET` 原文或 access token 原文 | 使用测试凭据执行一次成功调用，检查 stdout、stderr、MCP result 和 MCP error |
| AC-6 | 在 token 有效期内连续执行两次 tool 调用，只发生一次 token 获取行为 | 使用 mock HTTP 客户端统计认证请求次数 |
| AC-7 | 代表性只读调用收到 SCM 2xx 响应时，MCP result 保留 SCM 返回的顶层字段和值 | mock SCM 返回固定 JSON，断言 MCP result 中对应字段和值一致 |
| AC-8 | 代表性写调用收到 SCM 2xx 响应时，MCP result 包含 SCM 返回的成功结果；server 不额外声明 dry-run 或本地回滚 | mock 写操作返回固定 JSON，断言 MCP result 与返回体一致 |
| AC-9 | SCM 返回 401、403、404、409、5xx 时，MCP 返回 error，error 文本包含状态类别或状态码，不包含 Python traceback | 对每类状态码使用 mock 响应调用代表性 tool |
| AC-10 | SCM 网络不可达或超时时，任一 tool 调用在配置的超时时间内返回 MCP error | 将 SCM base URL 指向不可达地址或 mock timeout，记录返回时间和 error |
| AC-11 | 使用只读或低权限 token 调用写能力时，server 返回 SCM 权限错误，不重试、不切换凭据、不扩大权限 | mock 或集成环境返回 403，检查请求次数和错误内容 |
| AC-12 | 写操作 tool 的描述中包含"写操作"和"立即生效"等风险提示 | 导出 tool descriptor，检查写操作描述文本 |
| AC-13 | `openapi-specs/scm/` 中被引用的 YAML 文件缺失或引用路径不可解析时，schema 校验失败 | 临时移除或重命名引用 YAML，运行 schema 校验或相关测试 |
| AC-14 | `CLAUDE.md` 第 3 节目录约定包含 `docs/PRD.md`，且说明其职责为产品需求文档 | 检查 `CLAUDE.md` 目录树中的 `docs/PRD.md` 条目 |

---

## 5. 风险与待确认问题

### R1 — 凭据安全

**风险**：`SCM_CLIENT_ID`、`SCM_CLIENT_SECRET` 和 access token 若出现在日志、MCP 消息、错误堆栈、shell history 或版本库中，会扩大 SCM 租户暴露面。

**缓解方向**：

- 凭据唯一来源为环境变量，不写入代码、测试快照或文档示例中的真实值。
- 默认日志不输出 Authorization header、client secret 或 access token。
- access token 仅保存在进程内存，不落盘、不通过 MCP result 返回。
- `.env` 必须被版本控制忽略；示例文件只能包含占位值。

**待确认问题**：

- 生产部署是否要求接入外部 Secret Manager？
- 是否需要提供日志脱敏测试作为发布门禁？
- 是否需要规定 token 在进程退出、异常退出时的清理策略？

### R2 — 写操作防误触

**风险**：自然语言意图可能被 AI 助手误解，导致创建、更新、删除、移动、配置版本写操作或 IAM 写操作在 SCM 中立即生效。

**缓解方向**：

- 写操作 tool 描述必须明确标注"写操作"和"立即生效"。
- 读写能力在命名和描述上保持可区分，降低 AI 助手误选概率。
- 高风险能力应在 README 和 DESIGN.md 中标注风险级别。
- 推荐在 MCP 客户端侧让用户确认高风险写操作。

**待确认问题**：

- 是否在 server 层增加只读模式，例如 `SCM_READONLY=true`？
- 是否需要对 delete、move、配置版本写操作、IAM secret 重置引入二次确认机制？
- 是否需要提供 allow-list / deny-list 限制可调用的写能力集合？

### R3 — Token 权限边界

**风险**：Service Account 权限过宽时，MCP server 暴露的能力会继承该 token 的全部 SCM 权限；server 不具备独立权限隔离能力。

**缓解方向**：

- 文档建议为 MCP server 创建专用 Service Account。
- 按用户场景拆分只读 token、配置写 token、IAM 管理 token。
- SCM 返回权限不足时，server 只透传错误，不尝试提权或切换凭据。
- 验收中覆盖低权限 token 调用写能力的失败路径。

**待确认问题**：

- SCM IAM 是否支持 folder、resource type 或 operation 级别的精确授权？
- 是否需要为不同用户角色运行多个 server 实例并绑定不同凭据？
- IAM 管理员是否接受 MVP 暴露 IAM 写能力，还是要求先以只读模式上线？

### R4 — API 版本漂移

**风险**：`openapi-specs/scm/` 来自上游规范；当上游字段、枚举、请求体或端点行为变化时，本地 tool schema 可能与实际 SCM API 不一致。

**缓解方向**：

- `openapi-specs/` 保持只读，不在本仓库内手改规范。
- 每个 tool schema 必须记录来源 YAML，便于定位漂移影响面。
- 当 OpenAPI YAML 变更时，触发 schema 生成、路由完整性和代表性 tool 测试。
- DESIGN.md 作为 tool 到 REST 映射的唯一技术设计文档，PRD 不复制映射表。

**待确认问题**：

- 上游 `pan.dev` 规范是否有稳定 release、changelog 或 breaking change 通知？
- 本仓库是否固定到上游 commit，还是跟随分支更新？
- 是否需要在 CI 中加入 OpenAPI diff 报告并阻止未审查的 schema 变化？

### R5 — 审计与可追溯性

**风险**：MVP 不持久化操作记录；当写操作造成生产影响时，可能需要依赖 SCM 自身审计日志和 MCP 客户端上下文追溯。

**缓解方向**：

- MCP server 默认不保存请求体，避免扩大敏感数据面。
- README 明确说明审计主来源是 SCM 平台审计能力。
- 对高风险写操作建议用户保留 MCP 客户端对话记录或变更工单编号。

**待确认问题**：

- 是否需要在后续版本增加可选的结构化审计日志？
- 审计日志如落地，哪些字段必须脱敏或禁止记录？
