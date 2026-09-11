# 006-01: 服务端预�?下载端点拆分

**What to build:** 让视频产出从「一个端点什么都干」拆成语义明确的两个 HTTP 端点：`/video` 只做内嵌预览（inline 流，保留 Range），`/download` 做真正下载（attachment 流）。用户从此可以在页面里直接播放成片，下载则另走明确的下载端点�?
**Blocked by:** None (can start immediately)

**Status:** done

- [ ] `GET /api/tasks/{id}/video` 不再返回 `Content-Disposition: attachment`（纯 inline 预览），Range/206/416 逻辑�?`Accept-Ranges` 头保留，未完�?文件缺失�?404
- [ ] 新增 `GET /api/tasks/{id}/download`：校验任务存在且 done + 文件存在（否�?404），返回 `attachment; filename="{id}.mp4"` 的完整流
- [ ] 新增测试：`/video` �?attachment 头；`/download` 返回 attachment；未完成任务 `/download` 404