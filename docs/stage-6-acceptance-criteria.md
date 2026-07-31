# 阶段六验收标准

## 数据库

- 目标 project ref 再次确认为 `frzbbpocyzlqxljsrsiw`；
- `alembic upgrade head` 后版本为 `0003`；
- `users.auth_user_id` 为 nullable UUID、唯一，并以 `ON DELETE SET NULL` 引用
  `auth.users(id)`；
- 本地 disposable PostgreSQL 通过 upgrade、downgrade 和再次 upgrade；
- 远端现有水果、营养、季节和行为数据计数未被迁移意外改变；
- RLS、grants、policies 和 advisors 复核无新增高风险问题。

## 后端

- 无 token、伪造 token、错误 issuer/audience、过期 token 均不能访问业务 API；
- 有效 token 只能读取或修改自己的资料、偏好、推荐和反馈；
- 所有业务路由不接受身份用途的 `user_id`；
- `/health` 不需要登录且不泄漏配置；production 文档端点不可见；
- 完整 pytest 通过，错误响应不包含 token、数据库 URL 或内部堆栈。

## 前端

- 可注册、登录、恢复会话和退出；未登录访问业务路由会跳转登录；
- fetch 自动携带 access token，401 清理本地会话并返回登录页；
- 未配置 Auth 或 API 时显示可理解提示，不白屏、不请求 localhost；
- 不再使用 localStorage BIGINT user ID；
- `npm test` 和 GitHub Pages `npm run build` 成功；
- 公开构建产物只有 publishable key，没有数据库或高权限秘密。

## 部署与端到端

- FastAPI Cloud 最新 deployment 成功，数据库 health 为 `ok`；
- 匿名请求业务 API 返回 401，生产 docs/openapi 返回 404；
- GitHub Pages 三个公开变量配置完成，Actions 成功；
- 线上完成登录、建档、两种水果、刷新幂等、换组、反馈和历史验证；
- 最终 subagent 独立审计没有未解决的高优先级问题；
- Git 和构建产物秘密扫描通过，Supabase 系统 schema 未被修改。
