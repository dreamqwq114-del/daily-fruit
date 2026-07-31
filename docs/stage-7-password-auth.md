# 阶段七：免验证码的邮箱密码注册

## 目标与范围

目标 Supabase 项目为 `Daily Fruit`，project ref 为 `frzbbpocyzlqxljsrsiw`。本阶段只调整 Supabase Auth 的注册确认开关和 Vue 注册体验，不修改数据库结构、RLS、Alembic、seed 或业务表权限。

## Auth 配置决策

- 保持邮箱密码登录和新用户注册开启；
- 关闭 `Confirm email`，新注册必须立即返回 session；
- 保持匿名登录关闭；
- 保留密码找回邮件能力，不把注册确认与密码找回混为同一个开关。

## 前端合同

- `signUp()` 仅提交 `email` 和 `password`，不再提交 `emailRedirectTo`；
- 无显式 `next` 时，注册成功进入 `/onboarding`，登录成功进入 `/`；
- 如果注册响应没有 session，显示“注册配置异常，请稍后重试。”；
- Supabase Auth 的常见错误映射为中文，未知内部错误不直接展示给用户；
- `/auth/callback` 保留，普通注册不再使用。

## 安全取舍

关闭邮箱确认后，系统无法证明用户拥有所填邮箱。因此页面需提醒用户检查邮箱，并且不得把该邮箱当作已验证的联系方式。密码找回仍依赖邮件且可能受独立限流影响。

FastAPI JWT 校验、匿名用户拦截和用户数据隔离保持不变。前端只保存公开的 Supabase URL 和 publishable key，不得保存数据库密码或高权限密钥。

## 验收

1. 注册请求不包含 `emailRedirectTo`；
2. 注册返回 session 后直接进入建档；
3. 无 session 时不提示查收邮件；
4. 原有登录、退出、路由保护和 onboarding 回归通过；
5. 新注册不产生 `user_confirmation_requested` Auth 日志；
6. 一次性线上账号完成注册、建档、登出和再登录后被精确清理。
