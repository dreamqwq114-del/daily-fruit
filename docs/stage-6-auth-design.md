# 阶段六：认证与公网业务链路设计

## 目标与边界

S6 将 Supabase Auth、FastAPI Cloud 和 GitHub Pages 连接为可验证的公网链路。Vue
只使用 Supabase 客户端完成邮箱密码认证；水果、偏好、推荐、历史和反馈仍全部通过
FastAPI。浏览器不得获得 PostgreSQL 连接串、secret key 或 service role key。

## 身份流

1. Vue 使用 `VITE_SUPABASE_URL` 和公开的 publishable key 登录；
2. Supabase Auth 返回短期 access token，客户端库负责本地会话和刷新；
3. 统一 fetch 客户端发送 `Authorization: Bearer <access token>`；
4. FastAPI 从 Supabase JWKS 获取公钥，校验签名、issuer、audience、有效期、role、
   session ID 和 subject；
5. `sub` 解析为 UUID，并通过 `public.users.auth_user_id` 定位当前业务用户；
6. Router 不接受客户端提供的 `user_id`，Service 继续按内部 BIGINT 主键工作。

## 数据模型

- 保留 `public.users.id BIGINT`，避免改写现有外键和历史；
- 新增 `auth_user_id UUID NULL UNIQUE`；
- 外键指向 `auth.users(id)`，删除 Auth 账号时 `ON DELETE SET NULL`，历史数据不级联删除；
- 首次登录后 `POST /api/me` 创建绑定资料，之后重复创建返回 409；
- 迁移期间允许 NULL，避免破坏未来可能存在的旧演示资料。

## API 变化

- `POST/GET/PUT /api/me`；
- `GET/PUT /api/me/fruit-preferences`；
- `GET /api/me/recommendations`；
- 今日推荐和换组不再接收 `user_id`；
- 水果接口也要求有效登录；
- 反馈接口验证推荐项属于当前用户，不匹配时返回与不存在相同的 404；
- production 关闭 `/docs`、`/redoc` 和 `/openapi.json`。

## 安全与可用性

- FastAPI Cloud 仅配置项目 URL 和 JWT audience，不保存 publishable key；
- GitHub Pages 只配置公开的 API URL、Supabase URL 和 publishable key；
- JWKS 短时缓存，认证服务不可用返回统一 503，非法或过期 token 返回统一 401；
- public 业务表维持 RLS deny-by-default，浏览器角色不获得表权限，也不新增 Data API
  policy；
- 本地测试用独立 PostgreSQL 的最小 `auth.users` 兼容表，禁止连接正式 Supabase。

## 迁移与回滚

`0003` 只新增 nullable 字段、唯一约束和 `SET NULL` 外键。先在独立 PostgreSQL 验证
upgrade、downgrade、再次 upgrade，再对已确认的 Daily Fruit project ref 执行 upgrade。
生产回滚优先发布应用修复；只有确认没有绑定数据时才考虑 downgrade。
