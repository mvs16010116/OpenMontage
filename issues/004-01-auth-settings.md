# 004-01 - 认证 + 配置持久化骨架

**Status:** ready-for-agent  **Spec:** issues/004-narration-synth-lark-llm.md  **Blocking:** 无（02/03/04/05 依赖本票）

## 目标

搭建 Web 服务的认证层与配置中心：`admin / shiping@shiping` 登录、登出、改密；`/api/settings` 配置读写（lark base 坐标、字段映射、LLM、轮询）；前端登录页 + 配置页表单骨架。

## 验收标准

1. 启动时自动创建 `admin` 用户，密码 `shiping@shiping`（`pbkdf2` 哈希，不存明文）。
2. `POST /api/login` 正确/错误密码分别返回成功和 401；`POST /api/logout` 清除会话。
3. 除 `/api/login`、`/api/health`、`/`、静态资源外，所有接口在未登录时返回 401。
4. `GET /api/settings` 返回当前配置，`llm.api_key` 脱敏回显；`PUT /api/settings` 保存，`api_key` 入库前混淆。
5. 前端有登录视图（用户名/密码）与配置视图（base 配置、字段映射、LLM、轮询、改密区块），可保存并提示。
6. `web/requirements.txt` 增加 `itsdangerous`、`requests`。

## 文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `web/auth.py` | 新增 | 登录/登出/当前用户/改密/密码读写 |
| `web/db.py` | 改造 | `users`、`settings` 表；`settings` load/save |
| `web/server.py` | 改造 | SessionMiddleware、认证依赖、`/api/login`、`/api/logout`、`/api/settings` |
| `web/templates/index.html` | 改造 | 登录视图 + 配置视图骨架 |
| `web/requirements.txt` | 改造 | 新增依赖 |

## 验证

`python -m web.server` 启动；未登录访问受保护接口得 401；登录后可读写配置并改密。