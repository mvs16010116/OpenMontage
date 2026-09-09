# 004-06 - base_client Windows shim：cmd.exe 把 &view=… 链接切开

**Status:** done  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 004-02（损坏方）

## 目标

修复 `/api/base/scan` 在 Windows 上报 `lark-cli 失败：'view' 不是内部或外部命令`，让 Base 分享链接（含 `&view=…` 等查询参数）能正常解析与扫描。

## 方案与决策点

- **根因（Phase 3 假设，经复现确认）**：`web/base_client.py` 用 `shutil.which("lark-cli")` 取到 npm 的 `lark-cli.CMD` shim；subprocess 经 `cmd.exe` 执行时，`cmd` 把参数里的 `&` 当命令分隔符，于是 `…?table=xx&view=vew1` 被拆成两段——CLI 本身跑完并正常输出 JSON，而 `view` 被当作新命令报「不是内部或外部命令」写进 stderr，`_readable_error` 就把它当成了失败。
- 备选（被否）：对参数做 `^` 转义跑回 shim——要改 `_run` 的 cmd 语义、易漏其余元字符（`|<>^`），且只对 .cmd 路径生效。
- **方案**：新增 `_unwrap_shim(exe)`，`.cmd`/`.bat` 时在 shim 同目录/`node_modules`（含 scoped `@scope/<pkg>`）下找原生 `lark-cli.exe`，找到就直接调用（不再经 cmd.exe，argv 原样传递）；找不到才回退原 shim。`_resolve_bin` 改为先 `which` 再 unwrap。

## 验收标准

1. `_resolve_bin()` 返回原生 `…\node_modules\@larksuite\cli\bin\lark-cli.exe` 而非 `.CMD`。
2. 带 `&view=` 的分享 URL 经 `_run_json` 调 `+url-resolve` 返回正常 JSON，stderr 无 `view` 报错。
3. `tests/web/` 全绿（81 passed），含 `_run` 回归：cmd[0]==原生 exe 且 `--url` 值含 `&view=` 原样传递。

## 验证

- 修复前红色复现：`subprocess.run([…lark-cli.CMD, 'base', '+url-resolve', '--url', '…&view=vew1', …])` → rc=1，stderr 为 `'view' 不是内部或外部命令`（CLI stdout 实为 ok 的 JSON）。
- 修复后：`_resolve_bin()` 指向 exe；同 URL `_run_json` 返回 `{"ok": true, …, "base_token": …}`，无 shell 错误。
- 新增单测 6 条（`test_base_client.py`：unwrap 分支 4 + resolve/`_run` 回归 2）；全量 **81 passed**。
- commit：见 `issues/004-06` 提交（代码+测试+证据）。