# 004 - 飞书多维表格驱动的口播视频流水线（Lark Base + LLM + Web 管理）

**Date:** 2026-09-08  **Status:** spec-ready  **Branch:** main

## 目标与约束

将现有 `narration-synth` Web 服务从「文本框粘贴文案 → 视频」升级为「**飞书多维表格 → 视频流水线 → 回填结果**」的自动化生产线，并把 LLM 引入文案分节与图片关键词提取。

### 核心目标
1. **数据源为飞书多维表格**：每行一条口播文案，系统扫描待处理记录并按「文案日期字段」排序生成视频。
2. **字段映射可配置**：文案字段、日期字段、回填状态字段、附件字段，全部在 Web 页面配置（存数据库）。
3. **LLM 可配置化**：OpenAI 兼容接口（`base_url` + `api_key` + `model`），在 Web 页面配置，用于**文案分节 + 图片检索关键词提取**（取代现有硬编码 `KEYWORD_MAP` 与句号正则分节）。
4. **Web 登录**：用户名 `admin`，初始密码 `shiping@shiping`。
5. **进度可视化**：生成时前端显示进度条、**各阶段耗时**、**总耗时**。
6. **Token 统计**：视频生成成功后统计并展示本次消耗的 LLM token（prompt / completion / total）。
7. **结果回填**：生成成功/失败后回填状态字段；成功后把 `final.mp4` 上传到多维表格附件字段。
8. **预览与下载**：视频生成后可在网页 `<video>` 预览，也可下载。
9. **触发方式**：Web 手动触发（逐条/批量）+ worker 定时自动轮询多维表格。

### 约束
- **单用户、单任务串行**：沿用现有 APScheduler 串行执行，不做并发队列。
- **固定视频管线**：TTS 用 Edge TTS、配图用 Pexels、渲染用 HyperFrames、合成用 ffmpeg（与现有一致），不换后端。
- **配置存 SQLite**：配置（base 坐标、字段映射、LLM、轮询）全部持久化到 SQLite `settings` 表，不在代码里硬编码。
- **lark-cli 为唯一飞书通道**：通过 subprocess 调 `lark-cli base +...`（user 身份），不引入额外 SDK。
- **LLM 为硬依赖**：LLM 调用失败时任务报错并提示检查 LLM 配置，不静默降级到硬编码词典。
- **免登录推导**：初始密码只存哈希（`pbkdf2`），不存明文。

### 排除的功能（明确不集成）
| 排除项 | 原因 |
|--------|------|
| 多租户 / 多用户 | 单用户服务 |
| 找回密码 / 邮箱验证 / 双因素 | 超出需求 |
| 非 OpenAI 兼容的 LLM（Anthropic 原生、Gemini 原生等） | 统一走 `/chat/completions` |
| 视频内容质量评审 / 编辑决策 | 固定流水线 |
| Base 表单 / 仪表盘 / workflow 读写 | 只读写数据表记录 |
| 本地文件 → Base 批量导入 | 数据已存在于多维表格 |
| 并发多任务 | 串行 |
| BGM / 音效 | 现有一致，不加 |

## 方案与决策点

### 决策 1：认证 — FastAPI session cookie + pbkdf2 密码哈希（无额外重依赖）
- `POST /api/login`（`username`/`password`）→ 校验成功签发 session cookie；`POST /api/logout`。
- 密码哈希用标准库 `hashlib.pbkdf2_hmac`（随机盐，迭代 ≥100k），hash 存进 SQLite `users` 表。
- 首次启动自动创建 `admin` 用户，初始密码 `shiping@shiping`。
- API 层实现 `current_user` 依赖，除 `/api/login`、`/api/health`、`/`（静态首页）外的所有路由要求已登录，未登录返回 401。
- 允许用户登录后修改密码（配置页提供可选的「修改密码」区块）。
- 依赖 `itsdangerous`（session 签名），与 Starlette 内置 `SessionMiddleware` 配合。
- 被否：JWT 无状态 token（自托管单用户 session 更简单）；浏览器 Basic Auth（无法优雅登出/改密）。

### 决策 2：配置中心 — SQLite `settings` 表 + Web 配置页（存数据库、即时生效）
- 单行 JSON 配置，结构（URL/名称均为网页填写项）：
  - `lark`: `base_url_or_token`（分享链接或 base_token）、`table_id`
  - `fields`: `content_field`（文案）、`date_field`（日期/排序）、`status_field`（回填状态）、`attachment_field`（视频附件）、`date_sort`（`asc|desc`，默认 `asc` 先处理时间早的）
  - `llm`: `base_url`、`api_key`、`model`、（可选 `temperature`、`max_tokens`）
  - `poll`: `enabled`、`interval_seconds`（默认 300）、`max_records_per_batch`（默认 20）
  - `video`: `status_success`/`status_failed`/`status_processing` 文案（默认「成功/失败/处理中」），`pending_if` = 状态字段为空或等于「待处理」
- `GET /api/settings`（返回时 `llm.api_key` 脱敏回显 `****`）、`PUT /api/settings` 整体保存。
- `api_key` 入库前做轻量混淆（Base64 XOR 固定密钥），仅防静态泄露，不作为安全边界。
- 实现单例配置加载器，变更后立即生效（读取时从 DB 拉取，低频无缓存风险）。
- 被否：`config.yaml` 文件（用户明确要求网页配置）；环境变量（同样不满足网页配置要求）。

### 决策 3：Base 集成层 — subprocess 封装 `lark-cli base +...`（user 身份）
- 封装命令（全部以 `--as user` 调用，token 由 lark-cli 自动刷新）：
  - URL 解析：`+url-resolve --url <...>`（配置填 URL 时）或直接接受 base_token。
  - 读记录：`+record-list --base-token --table-id [--filter-json] [--sort]` —— 按日期字段排序、过滤待处理。
  - 回填：`+record-batch-update`（写状态字段）。
  - 上传：`+record-upload-attachment`（传 `final.mp4` 路径 → 追加附件字段）。
- 待处理判定：状态字段为空 或 等于「待处理」；日期字段用于排序；扫描数量受 `max_records_per_batch` 限制。
- 每次扫描输出 `[{record_id, title, content, date}]` 供前端展示；同时做**去重**：相同 `record_id` 若已有 `queued/running/done` 任务则跳过（DB `record_id` 记录）。
- 依赖提供：`lark-cli` 可执行文件在 PATH（npm 全局安装已验证），Windows 下用 `.cmd` 解析调用（沿用仓库 `_windows_cmd` 模式）。

### 决策 4：LLM 层 — OpenAI 兼容 `/chat/completions` + token 统计
- 轻量客户端（`requests`，不引入 `openai` SDK）：`POST {base_url}/chat/completions`，Bearer `api_key`。
- 一次调用完成一个文案的解析，`response_format` 请求 JSON 对象输出：
  ```json
  { "title": "短标题", "sections": [ {"text": "分节文本", "keywords": ["english keyword", "..."] } ] }
  ```
- 关键词为**英文**（供 Pexels 检索），每节 ≤3 个；分节以语义完整句为段，不分句号硬切。
- 解析 `usage.prompt_tokens / completion_tokens / total_tokens`，连同模型名写入任务。
- 失败处理：HTTP 错误/JSON 解析失败 → 抛异常终止任务并带清晰错误信息（提示检查 LLM 配置）。
- 被否：`openai` SDK（多一个重依赖，`requests` 足够）；本地模型（无 GPU 钱包约束、部署复杂度高）。

### 决策 5：pipeline 改造 — LLM 分节/关键词 取代硬编码 + 阶段计时
- `run_pipeline` 输入保持不变（text），但首步「分节+关键词」从运行 `parse_script`/`derive_keyword` 改为调用 LLM 层产出 `sections[]`（含 keywords）。
- Pexels 检索条件 = LLM 关键词（原 `derive_keyword` 硬编码映射删除或保留为未配置 LLM 时的 fallback —— **默认不 fallback，LLM 失败即失败**）。
- 每个阶段起点/终点打时间戳，`progress(stage, message, phase_duration_s, total_elapsed_s)` 上报；完成阶段把持续时间写入任务的 `stage_timings`。
- 关键阶段顺序（保持产物布局不变）：`llm_parse → generating_tts → fetching_images → rendering_scenes → subtitles → assembling → done`。
- 输出目录结构、产物命名与现有一致（`projects/<slug>/...`），新阶段 `llm_parse` 的原始 LLM 响应与解析结果落 `artifacts/script.json`。

### 决策 6：任务调度 — 手动 + 自动轮询（沿用 APScheduler）
- 手动：POST `/api/tasks`（从已扫描记录列表选 record_id，或直接传文案文本）；支持 `POST /api/tasks/batch` 批量。
- 自动：新增间隔任务，每周期读配置（若 `poll.enabled`）→ 扫描待处理 → 创建任务（受单任务串行约束，任务排队）。
- worker 执行完任务后追加**后置步骤**：写状态字段（成功/失败）→ 成功则上传视频附件；上传/回填失败不影响任务本体状态，但记入任务 `base_sync_status`（`ok|failed` + 错误）。
- 去重：`tasks.record_id` 唯一约束，重复创建返回既有任务。

### 决策 7：SSE 进度与统计展示
- SSE payload 扩展：`{stage, message, phase_duration_s, total_elapsed_s}`；`done` 事件带 `llm_usage`、`total_elapsed_s`。
- `stage_timings`（各阶段耗时表）+ 总耗时在任务详情/前端展示。
- token 统计随 `done` 落库，前端完成卡片展示。

### 决策 8：视频预览 + 下载
- `GET /api/tasks/{id}/video` 返回带 `Accept-Ranges` 的 `FileResponse`（FastAPI 原生支持），前端 `<video controls>` 直连 play，下载用同一 URL 的新标签页 `<a download>`。
- 预览/下载不限制已登录之外的条件。

### 决策 9：前端 — 单页三视图（vanilla HTML/JS，无构建步骤）
- **登录视图**：用户名/密码表单。
- **配置视图**：Base 配置（链接/token、table、字段映射、排序方向）、LLM 配置（base_url、api_key、model）、轮询配置（开关、间隔、批量上限）、修改密码。保存后即时生效并提示。
- **任务视图**：顶部「扫描多维表格」按钮 → 显示待处理记录列表（勾选 + 批量生成 / 逐条生成）→ 下方任务列表（状态、进度条、阶段耗时、总耗时、token、预览、下载）。
- 延续现有暗色样式与 `EventSource` 模式。

## 验收标准

### 功能验收
1. 未登录访问 `/api/tasks` 等接口返回 401；用 `admin / shiping@shiping` 登录成功并保持会话；登录后可改密码。
2. 配置页可保存/回填 base + 字段映射 + LLM + 轮询配置；`api_key` 回显脱敏。
3. 「扫描多维表格」返回按日期排序的待处理记录列表，重复扫描不产生重复任务。
4. 从待处理记录手动触发生成：进度条推进，显示每个阶段名称、各阶段耗时、总耗时。
5. 生成成功后在任务卡展示 LLM token 统计（prompt/completion/total 与模型名）。
6. 生成成功后 `final.mp4` 上传到多维表格附件字段，状态字段写「成功」；失败写「失败」。
7. 视频在网页 `<video>` 可预览可下载。
8. 开启自动轮询后，worker 按配置间隔自动扫描并为待处理记录建任务。

### 技术验收
9. `tasks` 表新增字段（`record_id`、`stage_timings`、`llm_usage`、`total_elapsed_s`、`base_sync_status`）且旧任务兼容。
10. 密码只存 `pbkdf2` 哈希不存明文；session cookie 签名。
11. LLM 调用失败、lark-cli 报错、视频生成失败各自给出可读错误，任务状态 `error`，状态字段回填「失败」。
12. `web` 目录新增依赖可 `pip install` 安装；`python -m web.server` 启动即用。

### 边界验收
13. 未配置 base/LLM 时，相关功能给出明确提示而非崩溃。
14. 单任务串行；同一 record 不重复入队。
15. 不引入外部服务（Redis/Celery/独立 DB）。

## 涉及文件（改造目标）
| 文件 | 操作 | 说明 |
|------|------|------|
| `web/server.py` | 改造 | 认证依赖、`/api/settings`、`/api/base/*`、任务路由、SSE 扩展 |
| `web/db.py` | 改造 | `users`、`settings` 表；`tasks` 扩展字段 |
| `web/auth.py` | 新增 | 登录/登出/当前用户/改密 |
| `web/base_client.py` | 新增 | lark-cli subprocess 封装（扫描/回填/上传） |
| `web/llm.py` | 新增 | OpenAI 兼容客户端 + token 统计 |
| `web/pipeline.py` | 改造 | LLM 分节/关键词；阶段计时 |
| `web/worker.py` | 改造 | 手动+自动轮询调度；后置回填/上传 |
| `web/templates/index.html` | 重写 | 三视图前端（登录/配置/任务） |
| `web/requirements.txt` | 改造 | 增加 `itsdangerous`、`requests` |
| `tests/web/test_api.py` | 扩展 | 认证、配置、扫描、任务、SSE 行为测试（mock lark-cli/LLM） |