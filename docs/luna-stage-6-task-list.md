# Luna 阶段六任务清单

每次只执行一个任务。失败时保留完整错误并停止，不通过关闭认证、放宽 grants/RLS、
删除测试或使用 service role 绕过。

## S6-01 JWT 验证与当前用户依赖

- 允许：`backend/app/auth/`、配置、错误类型和专项测试；
- 禁止：改数据库、前端和部署；
- 验证：JWT 签名、issuer、audience、时效、role、UUID 与失败关闭测试；
- 停止：无法确认 JWKS 规则或需要共享 JWT secret。

## S6-02 Auth 绑定迁移

- 允许：User model、Alembic `0003`、迁移/metadata 测试；
- 禁止：正式 Supabase 写入和 seed；
- 验证：本地 upgrade、downgrade、upgrade，字段/唯一/FK/delete action 一致；
- 停止：发现未知同名字段、非 `0002` 基线或真实用户数据。

## S6-03 API 所有权改造

- 允许：Router、Service、Repository、Schema 和 API 测试；
- 禁止：前端和远端部署；
- 验证：`/api/me`、无客户端 user ID、跨用户反馈 404、匿名 401、全量 pytest；
- 停止：必须信任请求体身份或需要开放浏览器数据库权限。

## S6-04 Vue Auth

- 允许：`frontend/src/auth/`、API 客户端、路由、登录相关页面、依赖和测试；
- 禁止：业务表直连和 service role；
- 验证：会话门禁、Bearer header、401、缺配置提示、npm test/build；
- 停止：只能通过高权限 key 或数据库 URL 才能运行。

## S6-05 生产迁移

- 允许：只对已确认 Daily Fruit 项目执行 `alembic upgrade head`；
- 禁止：Dashboard 手工改表、seed、降级、其他项目；
- 验证：版本、字段、约束、数据计数、RLS/grants/advisors；
- 停止：project ref、身份、基线或连接用途不一致。

## S6-06 FastAPI Cloud 部署

- 允许：必要公开配置、Secret 管理和部署文件；
- 禁止：在日志或 Git 输出秘密；
- 验证：health、DB health、匿名 401、docs 404、日志无泄漏；
- 停止：云端指向错误 Supabase 或构建日志暴露秘密。

## S6-07 Pages 与线上验收

- 允许：三个公开 repository variables 和 Pages workflow；
- 禁止：数据库/secret/service role 进入 `VITE_`；
- 验证：Actions、页面资源、Auth、完整业务 E2E 和移动端；
- 停止：后端未受保护、CORS 放宽到任意来源或只能伪造成功。

## S6-08 独立审计与交付

- 允许：只读审计、必要的最小修复、文档和提交；
- 验证：subagent 审查身份边界、迁移、前端密钥、部署和测试证据；
- 停止：存在未解决的高优先级安全或数据完整性问题。
