# 003 - narration-synth 口播视频生成 Web 服务

**Date:** 2026-09-08  **Status:** spec-ready  **Branch:** main

## 目标与约束

将当前 CLI 驱动的 narration-synth 视频生成流程封装为 **单用户 Web 服务**，只集成口播视频生成相关功能，排除无关能力。

### 核心目标
1. **输入**：用户在网页粘贴一段口播文案（文本），点击生成。
2. **输出**：系统自动完成分节 → TTS 配音 → Pexels 配图 → HyperFrames 场景渲染 → 字幕生成 → ffmpeg 合成，最终提供 `final.mp4` 下载。
3. **交互**：Web 界面（进度条 + 历史列表 + 下载）+ REST API（供脚本/飞书 webhook 调用）。

### 约束
- **单用户**：仅你一人使用，部署在自有服务器，不需鉴权/多租户/并发队列。
- **固定 pipeline**：只集成 `narration-synth`（口播文案 → 视频），不集成 montage/documentary/其他 pipeline。
- **固定配置**：视频分辨率 1920×1080、字幕字号 80、accent `#fbbf24`、TTS 免费 Edge TTS（`zh-CN-YunxiNeural`）、分节 = 按句号自动分段 — 全部硬编码，不暴露配置 UI。
- **无 BGM**：与现有一致，暂不集成音乐生成。
- **无审批/无 proposal 阶段**：用户直接输入文案，无需 idea/script 审批流程。
- **依赖**：Node ≥22（HyperFrames）、ffmpeg、Python 3.11+、`PEXELS_API_KEY`。TTS 用微软 Edge TTS（`edge-tts`，免费，无需 API key）。
- **状态管理**：复用 `projects/<slug>/` 目录结构，SQLite 记录任务元数据（轻量无外部 DB）。

### 排除的功能（明确不集成）
| 排除项 | 原因 |
|--------|------|
| Pipeline 清单/manifest 系统 | 单一 pipeline，无需路由 |
| Stage director skills / checkpoint / 审批门 | 单用户无人工审批需求 |
| Backlot board（只读看板） | 已有独立服务，不耦合 |
| 其他视频/图像 provider | 只用 Pexels 配图 |
| 音乐生成 | 现有 pipeline 无 BGM |
| Proposal/idea/script briefing 阶段 | 用户直接输入文案 |
| Edit decisions 抽象层 | 固定组装流程，无需决策 |
| 多租户/鉴权 | 单用户 |

## 方案与决策点

### 决策 1：后端框架选择 FastAPI（无争议）
- 理由：仓库已有 `backlot/server.py` 使用 FastAPI，生态熟悉，async 原生支持 SSE，单文件可启动。
- 替代方案（Flask/Django）：Flask 缺 async 原生；Django 太重，单用户无需 ORM/-admin。

### 决策 2：任务队列用 APScheduler（轻量，无 Redis/Celery）
- 单用户同一时间只有一个任务在跑，用 APScheduler 的 `BackgroundScheduler` 即可。
- 提交任务 → `scheduler.add_job(run_pipeline, ...)` → 任务状态写 SQLite → 前端 SSE 轮询/推送。
- 替代方案（Celery + Redis）：多用户/高并发才需要，单用户过度工程。
- 替代方案（asyncio.create_task）：进程重启会丢任务，不可靠。

### 决策 3：状态持久化用 SQLite + 项目目录
- SQLite 表 `tasks`：`id, status, narration_text, created_at, started_at, finished_at, output_path, error_message`。
- 项目目录 `projects/<slug>/` 保留所有中间产物（artifacts/、assets/、renders/），与现有结构一致。
- 替代方案（JSON 文件）：并发写入风险；PostgreSQL：单用户过度。

### 决策 4：SSE 推送进度（复用 backlot 模式）
- `/api/tasks/{id}/events` — SSE 端点，推送 pipeline 阶段变化。
- 阶段：`queued → parse_script → generating_tts → fetching_images → rendering_scenes → subtitles → assembling → done/error`。
- 前端用 `EventSource` 连接，更新进度条文字。

### 决策 5：TTS 用免费 Edge TTS（替代 Doubao，用户拍板）
- 原方案 Doubao 需要 `DOUBAO_SPEECH_API_KEY`（.env 中为空导致 pipeline 卡死）。
- 用户拍板改用 **微软 Edge TTS**（`edge-tts` Python 库）：免费、无需 key、中文男声 `zh-CN-YunxiNeural` 音质可接受。
- 每节单独合成 → `assets/audio/narration_section_0X.mp3`，用 ffprobe 探测真实时长重建分节窗口（`rewindow_script`），场景/字幕/adelay 全部以真实语音时长为准。
- 节间预留 `TTS_PAUSE_GAP=0.6s` 呼吸停顿（尾段停顿丢弃）。
- 替代方案（SiliconFlow）：用户先问过硅基流动，最终仍选免费的 Edge TTS。

### 决策 6：前端用 vanilla HTML/JS（无框架依赖）
- 单页面：textarea + 生成按钮 + 进度条 + 历史列表 + 下载链接。
- 无 React/Vue/Svelte 构建步骤，直接 FastAPI `StaticFiles` 挂载。
- 理由：单用户、功能简单、维护成本最低。

### 决策 7：Pipeline 核心逻辑抽取为独立模块
- `pipeline.py`：纯函数 `run_pipeline(task_id, narration_text) → output_path`。
- 内部按顺序调用：script segmentation → TTS → Pexels images → HyperFrames render → subtitle generation → ffmpeg assembly。
- 不依赖 FastAPI，可独立测试/复用。

## 验收标准

### 功能验收
1. 用户粘贴口播文案 → 点击"生成" → 进度条显示阶段 → 完成后可下载 `final.mp4`。
2. REST API：`POST /api/generate` 提交文案 → 返回 `task_id`；`GET /api/tasks/{id}` 查状态；`GET /api/tasks/{id}/video` 下载成片。
3. 历史列表显示所有生成过的任务（文案摘要、状态、时间、下载链接）。
4. SSE 进度推送正常工作（前端实时更新阶段文字）。

### 技术验收
5. 生成的视频质量与 CLI 路径一致：1920×1080、h264、aac、字幕白像素 ≥4000、narration dB 在正常范围。
6. `projects/<slug>/` 目录结构与 CLI 路径一致（可复用现有工具链）。
7. 任务中断/失败时 SQLite 状态正确标记 `error`，不留下半成品。

### 边界验收
8. 不依赖 Redis/Celery/Docker 等外部服务（仅 Node + ffmpeg + Python）。
9. 同一时间只跑一个任务（串行执行，无并发冲突）。
10. 不暴露任何配置 UI（分辨率/字号/音色等全部硬编码）。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/server.py` | 新增 | FastAPI 应用（路由 + SSE + 静态文件） |
| `web/worker.py` | 新增 | APScheduler 后台任务 runner |
| `web/db.py` | 新增 | SQLite CRUD（tasks 表） |
| `web/pipeline.py` | 新增 | Pipeline 核心逻辑（text → final.mp4） |
| `web/templates/index.html` | 新增 | 单页面前端 |
| `web/requirements.txt` | 新增 | Python 依赖 |
| `web/README.md` | 新增 | 启动/使用说明 |
