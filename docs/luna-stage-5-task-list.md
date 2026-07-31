# Luna 阶段五任务清单

一次只执行一个任务。每个任务开始前检查 Git 状态，结束后运行指定测试并提交。

## S5-00 设计门禁

- 允许修改：`docs/stage-5-*`、`docs/luna-stage-5-task-list.md`；
- 禁止：Vue 业务实现、数据库操作；
- 验收：设计覆盖路由、API、错误、会话、安全和独立审计门禁；
- 停止：发现现有 API 无法支持页面且需要 schema 变化。

## S5-01 前端基础

- 允许修改：`frontend/package*.json`、`src/main.js`、`src/App.vue`、
  `src/router/`、`src/api/`、`src/utils/`、`vite.config.js`；
- 实现：Vue Router、统一 fetch、超时、API 模块、user ID 工具、基础导航；
- 禁止：正式页面细节、Supabase 客户端、前端推荐计算；
- 运行：`npm run build`；
- 停止：API 字段与现有 Pydantic Schema 冲突。

## S5-02 初始设置与偏好

- 允许修改：`src/views/OnboardingView.vue`、`PreferencesView.vue`、相关组件和 CSS；
- 实现：用户资料、口味、价格、便利度、水果状态和分步保存恢复；
- 禁止：正式认证、数据库直连；
- 验收：创建与更新流程可重试，偏好无重复 fruit ID；
- 停止：需要改变后端事务或数据库结构。

## S5-03 今日推荐

- 允许修改：`TodayView.vue`、`FruitCard.vue`、`NutritionTags.vue`、
  `RecommendationReasons.vue`、`FeedbackButtons.vue` 和 CSS；
- 实现：两张卡片、理由、营养、换组、五种主要反馈；
- 禁止：在 Vue 重算分数或理由；
- 验收：刷新幂等，按钮防连点，反馈去重；
- 停止：推荐响应缺少页面必需字段。

## S5-04 历史与共用状态

- 允许修改：`HistoryView.vue`、Loading/Error/Empty 组件和 CSS；
- 实现：历史、状态、理由、反馈、加载/空/错误；
- 验收：空历史和 replaced 清楚可辨；
- 停止：历史接口需要无界分页或额外数据库查询。

## S5-05 手机适配与本地验收

- 允许修改：前端样式、可访问性属性、README 阶段说明；
- 运行：前端 build、后端全量 pytest、本地 FastAPI 流程；
- 验收：320/375/768 宽度、后端离线、超时和重复点击；
- 禁止：远端 Supabase 写入和公开部署后端。

## S5-06 独立审计与部署

- 先调用 subagent 只读审计 S5；
- 只修复审计确认的问题，不做无关重构；
- 修复后重新运行 build 和相关测试；
- 使用既有 Sites 项目保存并部署私有版本；
- 验收：部署成功，入口与静态资源可访问；
- 停止：发现 secret、数据库身份不明、高优先级功能/安全缺陷或需要数据库修改。

