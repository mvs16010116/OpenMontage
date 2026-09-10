# 005-01 — edge-tts 调用加超时并清理 0 字节残留

**What to build:** 任何一次 TTS 合成调用都能在 60 秒内收敛（成功或明确失败），不再因网络挂起永久占用串行 worker 锁；失败/超时时把先写出来的 0 字节 mp3 删掉，避免后续阶段误判为有效音频。

**Blocked by:** None — can start immediately

**Status:** done

- [x] 对正常文本，`_synthesize_edge` 仍在合理时间内产出非空 mp3，返回时长 > 0 — 正常路径 23904B mp3 / dur 3.98s
- [x] 对模拟永不返回的 save（或短超时版本），在 ≤ 超时阈值时抛含 `timeout` 的 `RuntimeError` — `TTS_TIMEOUT_S=0.1` 探针 3.2s 抛 `RuntimeError("..timeout after 0.1s")`
- [x] 超时/异常路径会把同路径 0 字节残留文件删除 — 探针超时后残留被 `_cleanup_stale` 清除
- [x] 既有「单次重试」语义保留（第一次异常/超时后重试一次）— 保留内层 `except Exception: _cleanup_stale(); _run()`；重试的 `TimeoutError` 由外层 `except asyncio.TimeoutError` 捕获，消息正确