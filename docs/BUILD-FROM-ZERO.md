# 从 0 跟做：scm-mcp-server 构建手册

> 给想从头复现这个项目的人的「逐步轨迹」手册。
> 配合 git branch `scm-from-zero` 使用。

---

## 1. 总览

### 这是什么

一个 **MCP server**：把 Palo Alto Networks Strata Cloud Manager（SCM）已有的 REST API，封装成一组 MCP tools，供 Claude CLI / Cursor 等 MCP 客户端通过自然语言调用。它**不是**新平台——只做「刷 token → 组装请求 → 调 SCM REST → 透传响应」。

### 最终成果

- **Batch 1**（MVP，~58 个 tool）：覆盖 Objects（核心对象 CRUD + 扩展对象只读）/ Security（规则完整 CRUD + 所有安全配置文件）/ Operations / IAM 四个 API 域。
- **Batch 2**（扩展，~134 个 tool）：Objects 扩展写操作、Security 档案类写操作等。
- 语法检查：所有源文件 `ast.parse` 通过。
- 路由完整性：所有注册 tool 都有对应路由条目，无孤立项。

### 技术栈（钉死，引 `CLAUDE.md` §2）

| 项 | 选定 |
| --- | --- |
| 语言 | Python 3.11+ |
| MCP | 官方 `mcp` SDK |
| 传输 | stdio（唯一） |
| HTTP | `httpx` |
| 鉴权 | OAuth2 client_credentials（`auth.py` 自动管理） |

### 贯穿全程的四条红线（引 `CLAUDE.md` §4）

1. schema 唯一权威来源是 `openapi-specs/scm/` YAML，不手抄、不臆造。
2. 只转调 REST，不重写 SCM 业务逻辑。
3. 不硬编码地址与凭据，走环境变量。
4. 只用 stdio。

### 分层文档（Context Stack）

- **L1 `CLAUDE.md`**：工程契约（技术栈/红线/目录）。
- **L2 `DESIGN.md`**：tool ↔ REST 端点映射表（37 条）。
- **L3 `WORKFLOW.md`**：阶段协议（阶段 1 契约同步 → 2 实现 → 3 验收）+ 验收记录。
- `docs/PRD.md`：产品需求。`README.md`：怎么跑/怎么注册。

---

## 2. 前置条件：下载 OpenAPI 规范文件

> **必须在 Step 0 之前完成。** 后续所有步骤的 schema 来源都依赖这些文件；若缺失，AI 无法从 YAML 现查字段定义，只能靠"印象"臆造，导致代码跑不通。

### 为什么需要这一步

本项目的 `openapi-specs` 是一个软链接，指向同级目录 `../pan.dev/openapi-specs/`。原始文件托管在 PAN 官方 GitHub 仓库：

> **[https://github.com/PaloAltoNetworks/pan.dev/tree/master/openapi-specs](https://github.com/PaloAltoNetworks/pan.dev/tree/master/openapi-specs)**

pan.dev 仓库体积较大（含大量文档站资产），**推荐用 sparse checkout 只下载 `openapi-specs/` 子目录**，约 20–30 MB，完整克隆约 1 GB+。

### 下载步骤（sparse checkout，推荐）

```bash
# 1. 在项目的上级目录操作（与 vibecoding-mcp-server/ 并列）
cd /path/to/AI   # 替换为你自己的路径，例如 ~/projects

# 2. 初始化 sparse clone（只拉元数据，不拉文件内容）
git clone --filter=blob:none --sparse \
  https://github.com/PaloAltoNetworks/pan.dev.git

# 3. 进入仓库，指定只检出 openapi-specs/ 目录
cd pan.dev
git sparse-checkout set openapi-specs

# 4. 验证关键文件存在
ls openapi-specs/scm/config/sase/objects/
ls openapi-specs/scm/config/sase/security/
ls openapi-specs/scm/iam/
```

完成后目录结构应为：

```
AI/                              ← 你的工作目录
├── pan.dev/
│   └── openapi-specs/
│       └── scm/
│           ├── auth/AuthService.yaml
│           ├── config/sase/objects/objects-june.yaml
│           ├── config/sase/security/security-services-R2-2026.yaml
│           ├── config/sase/operations/config-operations-march.yaml
│           └── iam/ServiceAccounts.yaml  Roles.yaml  AccessPolicies.yaml
└── vibecoding-mcp-server/
    └── openapi-specs -> ../pan.dev/openapi-specs  ← 软链接（已建好）
```

软链接 `openapi-specs` 在仓库中已建好，pan.dev 放到正确位置后会自动生效，无需手动操作。

### 验证软链接是否正常

```bash
cd vibecoding-mcp-server
ls -la openapi-specs        # 应显示 -> ../pan.dev/openapi-specs
ls openapi-specs/scm/       # 应能列出 auth/ config/ iam/ 等子目录
```

如果 `ls openapi-specs/scm/` 报错，说明 pan.dev 的位置不对——检查它是否与 `vibecoding-mcp-server/` 在同一个父目录下。

### 如果不想用软链接

也可以直接把 openapi-specs 内容放进项目目录：

```bash
# 在项目根目录执行
rm openapi-specs                          # 删掉软链接
cp -r ../pan.dev/openapi-specs ./openapi-specs   # 复制实体目录
```

复制后记得在 `.gitignore` 里加上 `openapi-specs/`，避免把几十 MB 的 YAML 推进仓库。

---

## 3. 逐步轨迹

> 每节：**真实提示词（逐字，可直接复制）** → 关键决策/教学点 → 验收 → **commit / tag / push**。
> ⚠️ 下面的提示词是构建时**原样使用**的——红线约束、⚠️ 副作用提醒、"先给计划我确认"的 gating 一字未删。
> 照抄即可复现同样的轨迹；删掉这些约束，复现质量会下降。

### Git 提交规范（每步必做）

> **每完成一个 Step，必须执行以下三步后再继续下一步。轨迹不落盘，复现就会断。**

```bash
# 1. 提交（message 格式：step-N: 一句话描述）
git add -A
git commit -m "step-N: <本步描述>"

# 2. 打 tag（轻量 tag，名称与 step 号对应）
git tag step-N

# 3. 推送 commit 和 tag
git push origin scm
git push origin step-N
```

Tag 命名约定：

| Step | Tag | 描述 |
|---|---|---|
| Step 0 | `step-0` | Context Stack 契约 |
| Step 1 | `step-1` | PRD |
| Step 2 | `step-2` | 项目骨架 |
| Step 3 | `step-3` | DESIGN 映射表填充（Batch 1 + Batch 2 全部列出）|
| Step 4a | `step-4a` | 全域只读 tool（list_* / get_*）|
| Step 4b | `step-4b` | 全域标准写操作 tool（create_* / update_* / delete_*）|
| Step 5 | `step-5` | 特殊操作 tool（move_* / push_* / 有独特 body 的写操作）+ Batch 1 收口 |
| Step 5b | `step-5b` | Batch 2 扩展 tool（Objects 扩展 + Security 档案类写操作）|
| Step 6 | `step-6` | 阶段 3 收口 + 冒烟 |
| Step 7 | `step-7` | 注册到 Claude CLI + 端到端调用验证 |

检出任意历史节点：`git checkout step-N`

---

### Step 0 — Context Stack 契约

**真实提示词（逐字）**：

```
你是架构助手。我要给 Palo Alto Networks Strata Cloud Manager（SCM）写一个 MCP server。

要求：先不要输出任何代码，只输出计划（要建哪些文件、每个文件写什么）；我确认后你再生成；最后告诉我怎么验收。

要建的文件（对应 Context Stack 分层）：
a. CLAUDE.md — L1 工程契约（项目身份、技术栈不要换、目录约定、禁止事项、必须执行）
b. DESIGN.md — L2 设计（暴露哪些 MCP tool，各自包哪个 REST 端点，入参/出参）
c. WORKFLOW.md — L3 阶段协议
d. README.md — 给人看：怎么跑、怎么在 Claude CLI / Cursor 里注册

技术栈（请在 CLAUDE.md 钉死）：Python，官方 mcp SDK，stdio 传输，httpx HTTP 客户端。

关键约束：
- tool 的入参/出参 schema 唯一来源是 openapi-specs/scm/ 下的 YAML 文件，不要手抄、不要臆造。
- 只通过 REST 调用 SCM，不重写业务逻辑。
- SCM 使用 OAuth2 client_credentials，凭据走环境变量 SCM_CLIENT_ID / SCM_CLIENT_SECRET / SCM_TSG_ID。
- SCM API 基址走环境变量 SCM_BASE_URL，默认 https://api.strata.paloaltonetworks.com，不硬编码。

OpenAPI 规范位于本仓库同级目录 ../pan.dev/openapi-specs/scm/，子目录包含 auth/、config/（sase/ngfw/cloudngfw 等）、iam/ 等分类。
```

**教学点**：先立**契约**再写任何代码。L1 钉死不可变项，下层服从上层。DESIGN 映射表此时是空骨架——**故意的**，留给阶段 1 用 openapi-specs YAML 填。与日志分析版的关键区别：SCM 需要 OAuth2（auth.py 单独成文件），这是 L1 就要钉死的架构决策。

**验收**：4 文件齐、红线可读、OAuth2 凭据读取方式明确。

**提交**：
```bash
git add -A && git commit -m "step-0: 建立 Context Stack 契约（CLAUDE/DESIGN/WORKFLOW/README）"
git tag step-0 && git push origin scm && git push origin step-0
```

---

### Step 1 — PRD

**真实提示词（逐字）**：

```
基于 CLAUDE.md，你现在是产品与架构助手。请不要写代码。

先输出计划，再生成 docs/PRD.md，内容包含：
1. 目标用户与核心场景（网络安全工程师 / 平台运维 / 安全架构师 / IAM 管理员）
2. MVP 功能边界（明确 in scope / out of scope）。用能力描述，具体端点清单以 openapi-specs/scm/ YAML 为准，本文件不列举/不臆造端点。
3. 产品级数据流（用户 → MCP → SCM REST → 结果）。技术性的 tool↔REST 端点映射属于 DESIGN.md，本文件只引用、不重画。
4. 验收标准（每条可观察、可验证，禁用"流畅"等主观词）。
5. 风险与待确认问题（重点关注：凭据安全、写操作防误触、token 权限边界、API 版本漂移）。

另外：把 docs/PRD.md 补进 CLAUDE.md 第 3 节目录约定，保持 L1 自洽。
```

**教学点**：PRD 写**能力**不写端点——端点是 L2 的事，避免跨层重复与臆造。验收标准必须二元可判定。SCM 是生产系统，PRD 里要显式标注写操作风险（误触配置推送等）。

**验收**：验收标准 A1–A7 每条可执行；PRD 不含端点清单；风险表含凭据和写操作条目。

**提交**：
```bash
git add -A && git commit -m "step-1: 新增 docs/PRD.md，更新 CLAUDE.md 目录约定"
git tag step-1 && git push origin scm && git push origin step-1
```

---

### Step 2 — 项目骨架

**真实提示词（逐字）**：

```
基于 docs/PRD.md、DESIGN.md 和 CLAUDE.md 的目录约定，生成项目骨架（仅结构，不含具体业务 tool）。

先列完整目录树让我确认，再生成关键文件，最后给可执行的验收命令。

骨架范围（务必遵守）：
- 产出：目录结构、pyproject.toml、.env.example（含 SCM_CLIENT_ID/SCM_CLIENT_SECRET/SCM_TSG_ID/SCM_BASE_URL）、以下 5 个模块骨架：
  - config.py：读取 5 个 SCM 环境变量（BASE_URL/AUTH_URL/CLIENT_ID/SECRET/TSG_ID），缺必填项时 raise RuntimeError
  - auth.py：OAuth2 client_credentials 骨架（_fetch_token 调 /auth/v1/oauth2/access_token，get_token 做缓存+刷新，bearer_headers 返回 headers 字典）；token 有效期 15 分钟，提前 60s 刷新，threading.Lock 保证线程安全
  - rest_client.py：request(method, full_path, *, params, json) → (status, body)，注入 bearer_headers，不抛非 2xx
  - server.py：官方 mcp SDK + stdio，list_tools 返回空列表（TODO 占位），call_tool 分发到 tools.call
  - check.py：连通性自检（获取 token + 调一次 GET /config/operations/v1/jobs），退出码 0/1
- 不要生成任何具体 tool。tool↔端点映射当前为 _TBD_，其填充是 WORKFLOW.md 阶段 1 的第一步。

验收命令需可实际运行：pip install -e .、python -m scm_mcp_server.check（配好凭据后）、stdio 启动不报错、tools/list 返回空列表。
```

**教学点**：骨架先于 tool。`auth.py` 独立成模块是 SCM 与日志分析版的最大区别——OAuth2 刷新逻辑有状态（缓存 + 锁），不应混进 rest_client。`check.py` 的自检分两步：先拿 token（验证凭据），再调 API（验证权限），两步分开报错让故障更易定位。

**验收**：`pip install -e .` 通过；`python -m scm_mcp_server.check` 在凭据正确时输出 `OK`；`tools/list` 返回 `[]`。

**提交**：
```bash
git add -A && git commit -m "step-2: 搭项目骨架（config/auth/rest_client/server/check，tools 空列表占位）"
git tag step-2 && git push origin scm && git push origin step-2
```

---

### Step 3 — 阅读 OpenAPI 规范 + 填写 DESIGN 映射表

**真实提示词（逐字）**：

```
执行 WORKFLOW.md 阶段 1：契约同步。请不要写任何代码。

阅读以下 openapi-specs/scm/ 下的 YAML 文件，提取需要暴露为 MCP tool 的端点，填充 DESIGN.md §3 映射表：
- auth/AuthService.yaml（仅供 auth.py 内部使用，不暴露 tool）
- config/sase/objects/objects-june.yaml
- config/sase/security/security-services-R2-2026.yaml
- config/sase/operations/config-operations-march.yaml
- iam/ServiceAccounts.yaml、iam/Roles.yaml、iam/AccessPolicies.yaml

提取与排除原则：
- 每个 (path, method) → 一个 tool，命名为 {动作}_{资源}（小写下划线）
- 只读 tool（GET）和写操作（POST/PUT/PATCH/DELETE）全部纳入；写操作 description 标注「⚠️ 写操作」
- move 类端点（POST .../move）单独一行，命名 move_{资源}
- Auth token 端点（/auth/v1/oauth2/*）不暴露，由 auth.py 内部处理
- SASE deployment / mobile agent / network infrastructure 等高复杂度写操作暂列为"后续批次"
- 每行记录：tool 名、HTTP 方法+路径、类型（只读/写）、OpenAPI YAML 引用位置
- 映射表按 Batch 分两组：
  - **Batch 1（MVP）**：addresses、address_groups、services、service_groups、tags、app_groups、external_dynamic_lists（Objects 核心）+ security_rules 完整 CRUD + decryption_rules、app_override_rules、dos_protection_rules 完整 CRUD + 所有安全配置文件只读 + operations 全部（含 get_config_version、get_running_config_version）+ IAM 全部（含 get_service_account、get_role、get_access_policy）
  - **Batch 2（扩展）**：剩余 objects（applications、application_filters、schedules、regions、hip_objects、hip_profiles、log_forwarding_profiles 等）+ Security 档案类写操作
- 映射表填完后，统计两个 Batch 的 tool 总数，向我确认范围再进入阶段 2

先输出你提取到的端点清单和 tool 命名列表（按 Batch 分组），等我确认后再正式写入 DESIGN.md。
```

**教学点**：阶段 1 不只是"填表"，还包含**范围判断**——不是每个端点都该变成 tool。Auth 端点内部化不暴露是核心设计决策。用 Batch 分组而不是靠记忆决定哪些"应该有"，是防止遗漏的关键：**YAML 里有什么就列什么，再按复杂度分 Batch，而不是先拍脑袋定范围再去 YAML 里找**。

**验收**：DESIGN.md §3 无 `_TBD_`，Batch 1 / Batch 2 均已列出，每行可在对应 YAML 中定位；tool 命名符合 `{动作}_{资源}` 规范；move 类端点单独成行。

**提交**：
```bash
git add -A && git commit -m "step-3: 填充 DESIGN.md 映射表（Batch 1 + Batch 2，4 个 API 域）"
git tag step-3 && git push origin scm-from-zero && git push origin step-3
```

---

### Step 4a — 全域只读 tool（Batch 1 的所有 list_* / get_*）

**真实提示词（逐字）**：

```
执行 WORKFLOW.md 阶段 2：实现。先实现 DESIGN.md Batch 1 中全部只读 tool（list_* 和 get_* 类），跨 Objects / Security / Operations / IAM 四个域，不含写操作。服从 CLAUDE.md 红线。

先给实现计划（分几步，每步一个 commit），我确认后再逐步做。

约束：
- **以 DESIGN.md 映射表为唯一来源**，逐行实现，不跳过、不自行增减
- inputSchema 从对应端点的 YAML parameters 现查填写；folder/snippet/device/name/offset/limit 等公共查询参数用共享常量定义，不在每个 tool 里重复写
- tool 只做「组装请求 → rest_client.request → 透传响应」；非 2xx 按 DESIGN §4 返回 {error, status, body}
- 路由表驱动：_LIST_TOOLS = {tool名: (path, param_keys_tuple)}，_GET_BY_ID_TOOLS = {tool名: (path_template, param_keys_tuple)}；禁止 if/elif 分支
- list_* 的 path 含 {id} 以外的 path 参数（如安全配置文件的 profile name）也用 _GET_BY_ID_TOOLS，path_template 里用 {name} 占位
- 先搭 pytest 脚手架（mock rest_client.request），再实现 tool，每步跑测试
- 不实现任何写操作 tool（create_*/update_*/delete_*/move_*/push_*）
```

**教学点**：路由表驱动是本项目最重要的代码设计——工具数量可能超过 50 个，如果每个写一段 if/elif 代码会失控。`_LIST_TOOLS` / `_GET_BY_ID_TOOLS` 各自一行字典条目就能注册一个 tool。「以 DESIGN.md 为唯一来源」是防止遗漏的核心原则：不按域分批、不按记忆决定——只要 DESIGN 里有、就实现，DESIGN 里没有、就不做。

**验收**：`pytest -q` 通过（mock 层）；DESIGN.md Batch 1 的全部只读 tool 都在 `tools/list` 里；抽查 `list_addresses`（folder 参数）、`get_job`、`get_service_account` 有路由条目。

**提交**：
```bash
git add -A && git commit -m "step-4a: 实现 Batch 1 全域只读 tool（list/get 类，路由表驱动）"
git tag step-4a && git push origin scm-from-zero && git push origin step-4a
```

---

### Step 4b — 全域标准写操作 tool（Batch 1 的 create_* / update_* / delete_*）

**真实提示词（逐字）**：

```
继续实现 DESIGN.md Batch 1 中全部标准写操作 tool（create_* / update_* / delete_*），跨 Objects / Security / IAM 域。服从 CLAUDE.md 红线。

move_* 和 push_* 等特殊操作留给下一步，本步只做标准 CRUD 的写操作部分。

约束：
- **以 DESIGN.md 映射表为唯一来源**，逐行实现，不跳过、不自行增减
- inputSchema 从对应端点 YAML 的 requestBody schema 现查填写；只填 openapi 明确定义的字段，不臆造
- create_* tool：container 参数（folder/snippet/device）走 query params，body 字段走 JSON body，两者分开传
- update_* tool：id 在 path，body 只传调用方提供的非 None 字段（_pick 函数），不发平台已有值
- delete_* tool：id 在 path，无 body
- 路由表驱动：_CREATE_TOOLS = {tool名: (path, container_keys, body_keys)}，_UPDATE_TOOLS / _DELETE_TOOLS 类似
- 写操作的单测：mock rest_client.request，断言 method=POST/PUT/DELETE 及 body/params 内容；不做真实 SCM 调用（写操作有副作用，真实测试需 @integration 标注）
- description 里每个写操作 tool 都要标注「⚠️ 写操作」
```

**教学点**：SCM 写 API 的 container 参数（folder 等）走 query params 而不是 body——这是从 openapi YAML 现查得到的，不能臆造。`_pick()` 工具函数只取非 None 字段组装 body，让调用方只传要改的字段，不强制全量。「以 DESIGN.md 为唯一来源」同样适用：security_rules、decryption_rules、app_override_rules、dos_protection_rules 的 create/update/delete 都在这一步实现，不能漏。

**验收**：写操作 tool 单测（mock）全部通过；DESIGN.md Batch 1 的全部 create_*/update_*/delete_* 均有路由条目；抽查 `create_address`、`create_security_rule`、`delete_decryption_rule` 集成测试（`@integration`，默认跳过）可手动运行。

**提交**：
```bash
git add -A && git commit -m "step-4b: 实现 Batch 1 全域标准写操作 tool（create/update/delete，_pick 函数）"
git tag step-4b && git push origin scm-from-zero && git push origin step-4b
```

---

### Step 5 — 特殊操作 tool + Batch 1 收口

**真实提示词（逐字）**：

```
继续实现 DESIGN.md Batch 1 中剩余的特殊操作 tool，然后做 Batch 1 的路由完整性收口。服从 CLAUDE.md 红线。

特殊操作类型（需独立路由表 _MOVE_TOOLS / _PUSH_TOOLS 或单独处理）：
- move_security_rule（POST /config/security/v1/security-rules/{id}:move）
- move_decryption_rule（POST /config/security/v1/decryption-rules/{id}:move）
- move_app_override_rule（POST /config/security/v1/app-override-rules/{id}:move）
- push_candidate_config（POST /config/operations/v1/config-versions/candidate:push）

约束：
- **以 DESIGN.md 映射表为唯一来源**：只实现 Batch 1 里列出的特殊操作，不自行新增
- move_* tool 的 body 字段（destination、rulebase、where、pivot_rule_id）从对应 YAML 现查；description 标注「⚠️ 写操作，会改变规则顺序」
- push_candidate_config 的 body 字段从 config-operations-march.yaml 现查，不臆造；description 必须加「⚠️ 高风险写操作：会将候选配置下发到真实设备」
- 路由表驱动：_MOVE_TOOLS = {tool名: (path_template, body_keys)}；push_* 因参数特殊可单独实现
- 每步 commit + pytest 单测（mock），断言 method=POST 及 body/path 正确
- 收口：写一段断言，验证 DESIGN.md Batch 1 的全部 tool 名 == 当前已注册 tool 名集合，无遗漏、无多余
```

**教学点**：`push_candidate_config` 是本项目风险最高的 tool——它会真实下发配置到防火墙，description 里的 ⚠️ 警示让 Claude 在调用前向用户二次确认。`move_*` 系列是"同域 CRUD 之外"最容易被遗漏的操作——它们是 POST 请求但不是 create，需要单独路由表。收口断言是机械保证：不靠人工数，让程序验证 Batch 1 没有漏洞。

**验收**：Batch 1 全部 tool 注册完毕；路由完整性断言通过；`push_candidate_config` 单测验证 method=POST 且 body 字段正确；`move_security_rule` 单测验证 path 含 id 且 body 含 destination。

**提交**：
```bash
git add -A && git commit -m "step-5: 实现特殊操作 tool（move/push），完成 Batch 1 收口"
git tag step-5 && git push origin scm-from-zero && git push origin step-5
```

---

### Step 5b — Batch 2 扩展 tool（按需执行）

**真实提示词（逐字）**：

```
执行 DESIGN.md Batch 2：扩展 tool 实现。先实现只读部分，再实现写操作部分。服从 CLAUDE.md 红线。

先给实现计划（列出 Batch 2 中所有 tool，按域分组），我确认后再逐域实现。

约束：
- **以 DESIGN.md Batch 2 映射表为唯一来源**，逐行实现，不跳过、不自行增减
- 新 tool 沿用 Step 4a/4b 建立的路由表结构，只追加字典条目，不新建分支逻辑
- inputSchema 从对应端点 YAML 现查；Objects 扩展资源（applications、schedules、hip_objects 等）用 objects-june.yaml；Security 档案类（anti_spyware_profiles 等）用 security-services-R2-2026.yaml
- 写操作 tool description 标注「⚠️ 写操作」；push/move 类若有也单独处理
- 每新增一组资源（如 hip_objects）commit 一次 + pytest 跑通
- Batch 2 收口：更新路由完整性断言，覆盖 Batch 1 + Batch 2 全部 tool
```

**教学点**：Batch 2 的价值在于**路由表架构的可扩展性验证**——新增 60 个 tool 只需往字典里追加条目，不改任何分发逻辑。这证明了 Step 4a 建立的架构是对的。如果你发现需要改分发逻辑，说明架构有问题，要回头重构而不是打补丁。

**验收**：Batch 2 全部 tool 注册；路由完整性断言覆盖 Batch 1 + Batch 2；`pytest -q` 通过（mock 层）；抽查 `list_hip_objects`、`create_anti_spyware_profile` 有路由条目。

**提交**：
```bash
git add -A && git commit -m "step-5b: 实现 Batch 2 扩展 tool（Objects 扩展 + Security 档案类）"
git tag step-5b && git push origin scm-from-zero && git push origin step-5b
```

---

### Step 6 — 阶段 3 收口 + stdio 冒烟

**真实提示词（逐字）**：

```
执行 WORKFLOW.md 阶段 3：验收收口。先不扩新端点，把当前批次收口。先给计划我确认。

1. 语法自检：写一个内联脚本，对 scm_mcp_server/ 下全部 .py 文件跑 ast.parse，全通才算过。
2. 路由完整性验证：断言 TOOLS 列表中的 tool 名称集合 == 全部路由表的 key 合集，无遗漏、无多余。
3. stdio 冒烟（scripts/smoke_stdio.py）：用官方 mcp SDK 的 client over stdio 驱动本 server，跑完整握手：initialize → tools/list（断言 tool 数量与 DESIGN.md 一致，名称集合完全匹配）→ call_tool(list_jobs, {limit:1})，打印返回。证明它作为真实 MCP server 在传输层可用，而非只是直调 tools.call()。
4. 更新 README：补当前所有 tool 的分类列表；给出 Claude CLI / Cursor 的注册方式（command/args/env=SCM_*/）；加"连通性自检"一节。
5. 更新 WORKFLOW.md 验收记录：对照 docs/PRD.md §4 的 A1–A7 逐条标注结论 + 验证命令/证据。

约束：不新增 tool；不改已有 tool 行为；docs/ 相关文件一并检查是否需要同步更新。
完成后给 commit message。
```

**教学点**：冒烟用真实 MCP **client** 驱动 server，证明**传输层**可用（而非只直调 `tools.call()`）。路由完整性验证是"不漏 tool"的机械保证。tool 数量靠人工数容易出错，程序断言不会。Step 6 无论在 Batch 1 收口还是 Batch 2 完成后都可以重新执行——它是状态无关的质量门。

**验收**：`python -c "import ast, ..."` → 全部文件 OK；路由完整性 → All routing entries present；`python scripts/smoke_stdio.py` → SMOKE OK；WORKFLOW 验收记录 A1–A7 全部填写。

**提交**：
```bash
git add -A && git commit -m "step-6: 阶段 3 收口（语法检查 + 路由完整性 + 冒烟 + README + WORKFLOW 验收记录）"
git tag step-6 && git push origin scm && git push origin step-6
```

---

### Step 7 — 注册到 Claude 并做真实调用测试

**目标**：把 MCP server 接入 Claude，用自然语言完成一次端到端的真实 SCM 调用，确认整条链路（Claude → stdio → scm_mcp_server → SCM REST API）打通。

#### 7.1 用自然语言让 Claude 安装 MCP

你已经在用 Claude CLI 写这个项目了，直接在对话框里说：

```
帮我把当前目录下的 scm_mcp_server 注册为 MCP server，
命令是 python -m scm_mcp_server，
环境变量：
  SCM_CLIENT_ID=<你的 client id>
  SCM_CLIENT_SECRET=<你的 secret>
  SCM_TSG_ID=<你的 tsg id>
```

Claude 会自动修改配置文件并完成注册，无需手动编辑 JSON。

#### 7.2 重启 Claude 使配置生效

注册完成后，**完全退出再重新打开 Claude**（不能只关窗口）。重启后新的 MCP server 才会加载。

#### 7.3 调用测试（建议顺序）

重启后在新对话里依次测试：

```
用 scm MCP 列出 Prisma Access 文件夹下的前 5 个地址对象
```
预期：调用 `list_addresses`，返回地址列表，无报错。

```
查询 SCM 最近的配置推送任务状态
```
预期：调用 `list_jobs`，返回 job 列表和各任务状态。

```
在 Prisma Access 文件夹下创建一个测试地址对象，名称 test-from-mcp，ip_netmask 为 192.0.2.1/32
```
预期：调用 `create_address`，返回新对象 ID；可在 SCM 控制台确认对象已存在。

**提交**：
```bash
git add -A && git commit -m "step-7: 注册到 Claude，端到端调用验证通过"
git tag step-7 && git push origin scm-from-zero && git push origin step-7
```

---

## 4. SCM API 端点覆盖盘点

### Batch 1（MVP，随 Step 4–5 实现）

| 域 | 只读 tool | 写操作 tool |
| --- | --- | --- |
| Objects（核心） | list/get × 地址/地址组/服务/服务组/标签/应用组/EDL | create/update/delete × 地址/地址组/服务/服务组/标签 |
| Security | list/get × 安全规则/解密规则/应用覆盖规则/DoS防护规则 + list × 全部安全配置文件档案 | create/update/delete × 安全规则/解密规则/应用覆盖规则/DoS防护规则 + move × 安全规则/解密规则/应用覆盖规则 |
| Operations | list_jobs / get_job / list_config_versions / get_config_version / get_running_config_version | push_candidate_config（⚠️ 高风险）|
| IAM | list/get × 服务账号/角色/访问策略 | — |
| Auth | — | — 全部内化到 auth.py |

### Batch 2（扩展，Step 5b 实现）

| 域 | 资源 | 操作 |
| --- | --- | --- |
| Objects（扩展） | applications / application_filters / application_groups / schedules / regions / external_dynamic_lists / dynamic_user_groups / hip_objects / hip_profiles / http_server_profiles / log_forwarding_profiles / syslog_server_profiles | 各 5 个 CRUD（list/get/create/update/delete）|
| Security（档案类） | anti_spyware_profiles / anti_spyware_signatures / data_filtering_profiles / data_objects / decryption_exclusions / decryption_profiles / dns_security_profiles / dos_protection_profiles / file_blocking_profiles / http_header_profiles / profile_groups / url_access_profiles / url_categories / vulnerability_protection_profiles / vulnerability_protection_signatures / wildfire_anti_virus_profiles | 各 4–5 个 CRUD |

### 永久排除

| 原因 | 内容 |
| --- | --- |
| Auth 内部化 | 所有 `/auth/v1/oauth2/*` 端点，由 `auth.py` 处理，不暴露 tool |
| 高复杂度推迟 | SASE deployment、mobile agent、network infrastructure 配置类端点 |

---

## 5. 学生如何跟做

### 方式 A：对照已完成的仓库（最快）

```bash
# 0. 先下载 OpenAPI 规范（见 §2 前置条件）
#    确保 pan.dev/ 和 vibecoding-mcp-server/ 在同一父目录下

# 1. 克隆项目
git clone https://github.com/zm1990s/vibecoding-mcp-server.git
cd vibecoding-mcp-server
git checkout scm-from-zero

# 2. 验证软链接
ls openapi-specs/scm/   # 能列出子目录说明 pan.dev 位置正确

# 3. 配置凭据
cp .env.example .env
# 编辑 .env 填入 SCM_CLIENT_ID / SCM_CLIENT_SECRET / SCM_TSG_ID

# 4. 安装并自检
pip install -e .
export $(cat .env | grep -v '^#' | xargs)
python -m scm_mcp_server.check

# 5. 冒烟测试
python scripts/smoke_stdio.py
```

### 方式 B：用上面的提示词从零复现

> 先完成 §2 前置条件（下载 OpenAPI 规范），再按步骤执行。

按 Step 0 → Step 6 顺序，把每节"真实提示词"原样发给 Claude Code（或 Cursor），对照教学点和验收标准确认每步结果。

关键习惯：
- **每步先给计划、等确认后再执行**（提示词里的 gating 不要删）。
- **阶段 1（填表）和阶段 2（写代码）严格不混**：先确认 DESIGN 映射表完整，再写任何 tool 代码。
- **写操作默认不做真实集成测试**：需要真实调用时加 `@pytest.mark.integration` 且默认 deselect。

---

## 6. 常见问题

| 问题 | 原因 | 解决 |
| --- | --- | --- |
| `RuntimeError: 环境变量 SCM_CLIENT_ID 未设置` | 未配置凭据 | 检查 `.env` 或环境变量是否正确导出 |
| `HTTP 401` | token 无效或 TSG_ID 不匹配 | 确认 CLIENT_SECRET 正确；确认 TSG_ID 是服务账号有权限的 TSG |
| `HTTP 403` | 服务账号权限不足 | 在 SCM → IAM 为服务账号分配更高权限角色 |
| `HTTP 400` on list | folder/snippet/device 参数缺失 | SCM 列表 API 要求至少提供一个容器参数 |
| tool 在 MCP 客户端不出现 | 会话未重启 | 关闭重开会话；确认 `scm-mcp` 已在 MCP 配置中注册 |
| `push_candidate_config` 返回 409 | 有其他 job 正在运行 | 先用 `list_jobs` 确认无 pending/running job 再推送 |
| `ls openapi-specs/scm/` 报错或为空 | pan.dev 目录位置不对，软链接失效 | 确认 `pan.dev/` 与 `vibecoding-mcp-server/` 在同一父目录；或按 §2「不想用软链接」方案把 openapi-specs 复制到项目内 |
| sparse checkout 后 YAML 文件不存在 | sparse-checkout 路径未设置正确 | 在 pan.dev 目录执行 `git sparse-checkout set openapi-specs` 再 `git checkout` |

