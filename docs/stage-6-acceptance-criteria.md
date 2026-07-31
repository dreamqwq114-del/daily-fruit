# 阶段六验收标准

## 数据库

- 目标 project ref 再次确认为 `frzbbpocyzlqxljsrsiw`；
- `alembic upgrade head` 后版本为 `0004`；
- `users.auth_user_id` 为 nullable UUID、唯一，并以 `ON DELETE SET NULL` 引用
  `auth.users(id)`；
- 本地 disposable PostgreSQL 通过 upgrade、downgrade 和再次 upgrade；
- 远端现有水果、营养、季节和行为数据计数未被迁移意外改变；
- RLS、grants、policies 和 advisors 复核无新增高风险问题。

## 后端

- 无 token、伪造 token、错误 issuer/audience、过期 token 均不能访问业务 API；
- `is_anonymous=true` 的 Supabase 匿名 token 即使 role 为 authenticated 也返回 401；
- 有效 token 只能读取或修改自己的资料、偏好、推荐和反馈；
- 所有业务路由不接受身份用途的 `user_id`；
- `/health` 不需要登录且不泄漏配置；production 文档端点不可见；
- 完整 pytest 通过，错误响应不包含 token、数据库 URL 或内部堆栈。

## 前端

- 可注册、登录、恢复会话和退出；主动退出撤销服务端会话，未登录访问业务路由会跳转登录；
- fetch 自动携带 access token，401 清理本地会话并返回登录页；
- 未配置 Auth 或 API 时显示可理解提示，不白屏、不请求 localhost；
- 不再使用 localStorage BIGINT user ID；
- `npm test` 和 GitHub Pages `npm run build` 成功；
- 公开构建产物只有 publishable key，没有数据库或高权限秘密。

## 部署与端到端

- FastAPI Cloud 最新 deployment 成功，数据库 health 为 `ok`；
- 匿名请求业务 API 返回 401，生产 docs/openapi 返回 404；
- GitHub Pages 三个公开变量配置完成，Actions 成功；
- GitHub Pages 缺失 API、Supabase URL 或 publishable key 时构建必须失败；
- 线上完成登录、建档、两种水果、刷新幂等、换组、反馈和历史验证；
- 最终 subagent 独立审计没有未解决的高优先级问题；
- Git 和构建产物秘密扫描通过，Supabase 系统 schema 未被修改。

## 2026-07-31 验收结果

- 本地 disposable PostgreSQL 完成迁移往返验证，后端 `189 passed`；
- 前端 Node 测试 19 项、组件测试 12 项通过，Pages 生产构建成功；
- Supabase 为 `0004`，演示数据 24/24/48，Auth、业务用户及行为表在清理后均为 0；
- `auth_user_id` 的类型、nullable、唯一和 `SET NULL` 外键均已实查；
- anon/authenticated 对 public 表的 grants 为 0，安全 advisor 只有预期 INFO；
- FastAPI Cloud deployment 成功，health/database 为 200/ok，匿名 API 401，docs 404；
- Pages Actions run `30641162723` 成功，线上完成登录、建档、两卡、刷新幂等、喜欢反馈
  和换组；数据库确认 active/replaced 历史后已清理临时账号与行为数据；
- 云端日志扫描未发现错误、连接串、密码或高权限 key。
- 独立审计提出的主动退出、匿名身份、Pages 配置门禁及 401 清理顺序问题已完成代码修复与
  回归测试；主动退出失败会保留当前登录并向用户显示重试提示。
