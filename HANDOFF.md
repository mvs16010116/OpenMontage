# Handoff — OpenMontage

**Date:** 2026-09-10
**Branch:** main (005 全部 4 票完成并提交：`aec13a9`/`45eb3d7`/`afe618a`/`405be68`；已推至 origin/main)
**Next-session focus:** 真机全流程可用（服务已重启用新代码）。可让用户在 UI 重提 12 个失败任务，确认批量成功；观察 FFmpeg 孤立案是否复现。Tracker: issues/001..005。

---

## 1. What this session accomplished

### 005 — 「生成必失败」修复合闸（done，全部提交并已推送）
诊断结论 → spec `issues/005-narration-generation-reliability.md` → 4 票：
1. **005-01 (aec13a9)** `web/pipeline.py`：`_synthesize_edge` 加 `asyncio.wait_for(_, TTS_TIMEOUT_S=60)` + `_cleanup_stale()` 删 0 字节残留，保留单次重试；杜绝 edge-tts 网络挂起永久占 worker。验证：正常 23904B mp3；`TTS_TIMEOUT_S=0.1` 探针 3.2s 抛 `RuntimeError(timeout…)` 且残留被清；`tests/web` 100 passed。
2. **005-02 (45eb3d7)** gsap 404 根因：`composition.mjs` 未提交改动把 gsap 改成本地引用但 builder 从不拷文件。恢复 CDN `gsap@3.14.2` 标签 + 新增 `writeComposition(fs,pathMod,html,outputPath,vendorGsap)` 拷 `vendor/gsap.min.js` 兜底（`build_photo_carousel.mjs` 走它）。验证 `projects/005-accept/hyperframes/`：index.html 含 CDN URL、gsap 拷贝 md5 `b729ff7f59` 一致；`hyperframes lint` 0 error、`validate` 无 console errors；hyperframes compose 46 passed。
3. **005-03 (afe618a)** 卡死任务 b149087c33bd：SQLite 置 error（可读 error_message）+ 重启服务（旧进程 9428 无超时代码的线程持锁，仅改 DB 不够）→ 新 PID **13624**。重启后 12 任务无 running。
4. **005-04 (405be68)** 全链路回归通过：新任务 `77bb61948077` → done（150s），stage_timings llm_parse 3.65 / generating_tts 15.78 / fetching_images 0.03 / rendering_scenes 129.38 / subtitles 0.66 / assembling 12.31（秒）；`projects/narration-77bb61948077/renders/final.mp4` 513288B 1920x1080 h264+aac 10.9s；抽帧 signalstats YMIN=16 / YAVG≈29.6 / **YMAX=235**（有高亮白字，非黑帧）；`_video_master.mp4` 已 burn 字幕。**这是本批 12 个失败任务后首个端到端成功**。
- code-review（005-01..03）0 硬违规；判断调用 4 项（清理重复、fs/path 双导入、死 mkdir、writeText 重复）；Spec 2 项子代理断言被复读代码证伪（重试超时由外层捕获、005-03 为 ops 票 .db 不跟踪）、1 项接受权衡（existsSync 守卫若目录已有脏 gsap 不覆盖——删文件重跑即可）。

## 2. Key gotchas learned (do not re-hit)

（沿用 004-07/004-08 全部条目；本节新增本次教训）

- **服务只认 :8000，创建任务字段是 `narration_text`（不是 text）**；`POST /api/login` body `{"username":"admin","password":"shiping@shiping"}` 拿 session cookie；任务详情 `GET /api/tasks/<id>`、列表 `GET /api/tasks`（key=`id`）。命令以空格分隔参数（`--project 005-accept`，非 `--project=`）。
- **无 --reload 的服务重启后旧 PID 线程仍持 `_job_lock`**：改 DB 清卡死任务必须连服务进程一起重启，否则队列继续堵。
- **修环境类（gsap）先复现 Builder 失败，再动手**：005-02 曾误跑参数把产物写到 `projects/demo`，已 `git checkout --` 恢复；builder 参数解析只认空格风格。
- **帧非空判定用 signalstats**：`ts/yuvj` 下 `metadata=print` 必须配 `-f null -` 且从 stderr 抓 `lavfi.signalstats.YMAX`；JPEG→signalstats 直接可读，不需要先转 PNG。
- **PowerShell 无 heredoc**：临时脚本写 `%TEMP%\opencode\*.py` 再跑；`python -X utf8` 防 GBK 乱码。

## 3. Artifacts / files (reference these, don't duplicate)

- 005 改动：`web/pipeline.py`（TTS_TIMEOUT_S/_cleanup_stale/_synthesize_edge）、`.agents/skills/_military-shared/composition.mjs`（writeComposition/CDN 标签）、`.agents/skills/_military-shared/scripts/build_photo_carousel.mjs`、`.agents/skills/_military-shared/vendor/gsap.min.js`（新增 72779B）。
- 票据：`issues/005-narration-generation-reliability.md`（spec）`+ 005-01..005-04`（均 done）。
- 回归证据：`projects/narration-77bb61948077/`（渲染产物）、`projects/005-accept/`；临时验证 `%TEMP%\opencode\*005*`。
- 服务器：**PID 13624**（`python -X utf8 -m web.server`）；日志 `%TEMP%\opencode\webserver.log/.err.log`；运行时 db `web/narration_synth.db` gitignored。

## 4. Suggested skills for next agent

- `implement`（按票实现）、`handoff`、`code-review`（先自查，几何指标同 005 已内建）、`grilling`/`to-spec`/`to-tickets`。视频资产技能：`ass-subtitle-generator`、`military-*` 系列、`hyperframes`、`ai-video-gen`。

## 5. Open items / hygiene

- git 身份 `Dannyhiccpet <danny@hiccpet.com>`；只 stage 相关文件，工作区大量 `_tmp_*.py`/`.reasonix`/`.agents`/`projects` 无关（勿误提交）。
- **005 后遗留**：12 个历史失败任务（47bae a6b0687f1a8a b7e5f58dd339 c2568e170ad1 35193159f5f4 e97002f66ec5 46b7e82056c6 b9c18894c2f0 e16b38b66aea e334892abf2e f61014d5fdc7 b149）可在 UI 重提验证「批量成功」。其中 b149 已 error 可重提；47bae 为 FFmpeg 探针偶发孤案（观察中，复现再转票）。
- 真机可行点：配置真实多维表格 + LLM（base_url/model/api_key），开 `poll.enabled` 验证自动单任务轮询（当前 False）。lark-cli `--as user`（user=侯辉聪，openId `ou_bec77ebe8e7a0d5a6c41d620af4116a6`）。默认登录 admin / `shiping@shiping`。真实表 base_token `OZsLb287vaT2j8srKYXcyw05nkc`，table `tbl6rLRt9fdRbNa7`，record `fldC5GNO9A`，content 字段漂移中（曾见「优化文案」/「新闻改写」）。