# 用户偏好设置 V1 改造前审计

审计日期：2026-08-01

## 当前实现

- `PreferencesView.vue` 和 `OnboardingView.vue` 共用 `ProfileFields` 与
  `FruitPreferencePicker`。
- 基本信息目前包含 `username`、`city`、`region`、`price_level` 和
  `discovery_level`；城市仍被前端展示并作为必填字段提交。
- 地区下拉框包含“全国”。数据库已有用户中也存在历史 `region='全国'`，因此本次
  只在前端停止新增“全国”，不修改旧数据或删除 `users.city`。
- `convenience_preference` 表达用户对便利性的重视程度，但页面文案当前是“可以处理 /
  越方便越好”，需要改成更清晰的“不介意处理 / 越方便越好”。
- 水果页面已经去掉原始 select，但仍为 24 种水果逐项展示六组按钮，同时把
  `has_tried` 和 `willing_to_try` 暴露给本页面；这会让页面变长，也超出本任务的字段管理边界。
- 当前前端偏好转换器会把旧的非 2 分偏好保存在 `legacyPreferences`，并在保存时继续提交，
  需要改为只提交本页面管理的 favorite/dislike/forbidden 状态。

## 保存与兼容风险

- `PUT /api/me` 的 `UserUpdate` 已允许省略 `city`，但 `UserCreate` 仍要求城市；数据库
  `public.users.city` 为非空。本次应让新建用户在 API 边界省略城市，并由后端填充内部
  `UNKNOWN`，更新旧用户时省略城市即保持原值。
- `replace_preferences()` 当前对未提交的关系执行删除，并对已存在关系无条件覆盖
  `has_tried` 与 `willing_to_try`。这会丢失其他流程保存的熟悉度信息，必须改成字段级
  merge：本页面只清除/更新 `preference_score` 和 `is_forbidden`，保留其他字段。
- 未选择水果当前可能通过旧转换器形成中性或熟悉度记录；新页面必须只提交明确状态。
- 后端目前没有 favorite 数量上限和 forbidden/favorite 冲突校验；需要增加最多 5 个特别喜欢、
  以及明确冲突错误。

## 数据库现状

- 目标 Supabase 已确认是 Daily Fruit，project ref 为 `frzbbpocyzlqxljsrsiw`。
- 现有 Alembic 版本为 `0005`，`users` 已有 `discovery_level`，尚无
  `consumption_horizon_days`。
- 远端已有历史用户和水果偏好数据；本次不得删除关系记录、清空城市或重建偏好表。
- 新字段必须通过下一版 Alembic 迁移增加，旧用户默认 `discovery_level=1`、
  `consumption_horizon_days=4`。

## 推荐算法边界

本次不修改推荐评分、便利性匹配、季节、营养、价格、历史或反馈逻辑。新增消费周期只
采集并保存，暂不进入推荐排序。地区仍沿用现有中文值以保持季节匹配兼容；“暂不确定”
使用 `UNKNOWN`，不再新增 `全国` 用户值。

## 允许进入实现

审计未发现需要删除数据或无法确认目标数据库的阻塞，可以按目标文件的四阶段实施。
