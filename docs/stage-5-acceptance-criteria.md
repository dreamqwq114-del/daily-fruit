# 阶段五验收标准

## 路由与会话

- `/onboarding`、`/`、`/preferences`、`/history` 均可直接打开；
- 缺少或损坏的 localStorage user ID 会被安全处理；
- 未设置用户访问业务页会跳转初始设置；
- 只有用户明确 `404` 才清除 user ID；
- 页面刷新不会无条件创建新用户或新推荐。

## API 与状态

- 所有 fetch 位于 `frontend/src/api/`；
- 每个请求检查 `response.ok` 并有超时；
- 网络、超时、404、409、422、503 有友好且不泄密的消息；
- loading、error、empty、success 状态均有可见界面；
- 提交期间按钮禁用，快速重复点击不会产生并行提交；
- Vue 不包含推荐公式、数据库 URL 或 Supabase 高权限密钥。

## 功能

- 初始设置可创建用户并保存水果偏好；
- 今日页恰好显示 rank 1 和 2 的两种不同水果；
- 每项显示建议份量、营养演示标签和 2 到 4 条真实理由；
- 重新加载今日页返回同一 active recommendation ID；
- 换一组成功后 refresh number 增加且页面整体更新；
- eaten、liked、disliked、unavailable、expensive 均可提交；
- 重复同类型反馈不会在界面生成重复记录；
- 偏好页重新加载后与后端一致；
- 历史页显示 active/replaced、理由和反馈；
- 历史为空时不显示伪造内容。

## 视觉与质量

- 320px、375px、768px 宽度没有横向溢出；
- 所有表单字段和图标式按钮有可访问名称；
- 主触控按钮尺寸适合手机；
- 后端未启动时页面仍能解释问题并允许重试；
- `npm run build` 成功；
- 后端现有测试保持通过；
- 秘密扫描没有真实凭据；
- Git 工作区在提交后干净；
- 本阶段没有数据库迁移和远端 Supabase 写入。

## 独立审计门禁

最终部署前必须由 subagent 独立检查：

- API 字段和方法是否与 FastAPI 一致；
- 是否遗漏 loading/error/empty/重复提交；
- localStorage 失效和 404/503 是否区分；
- 是否有横向溢出、不可访问控件或过大组件；
- 是否意外引入 secret、Supabase 客户端或前端推荐逻辑；
- 构建和关键测试结果是否足以支持交付结论。

高优先级问题必须修复并重新验证后才能部署。

