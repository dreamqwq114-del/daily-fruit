# 源码地图

本表是教学结论到真实源码的索引。路径按仓库根目录写，函数名优先于行号；“事实类型”
只使用代码事实、migration 事实、测试事实、配置事实、设计推断和通用知识。

| 教学主题 | 教学结论 | 源文件 | 符号/对象 | 事实类型 | 对应章节 |
| --- | --- | --- | --- | --- | --- |
| 今日推荐生命周期 | 当天 active 存在时复用，否则生成 | `backend/app/services/recommendation_application_service.py` | `get_today_recommendation` | 代码事实 | 01、04 |
| 换组事务 | 旧 active 变 replaced，成功才 commit | 同上 | `refresh_recommendation` | 代码事实 | 04 |
| 用户级锁 | 按 user_id 获取事务 advisory lock | `backend/app/repositories/recommendation_repository.py` | `acquire_user_lock` | 代码事实 | 03、04 |
| 推荐持久化 | 领域结果映射成 ORM 主表和 items | `backend/app/services/recommendation_application_service.py` | `_persist_recommendation` | 代码事实 | 04 |
| 详情重载 | commit 后重新预加载完整图 | 同上 | `_load_detail` | 代码事实 | 03、04 |
| ORM → 用户领域对象 | 购买条件未进入算法输入 | `backend/app/services/recommendation_mapper.py` | `user_to_recommendation_input` | 代码事实 | 01、05 |
| ORM → 水果领域对象 | 缺失营养/供应状态保留明确语义 | 同上 | `fruit_to_recommendation_input` | 代码事实 | 01、03 |
| Facade | 外部从稳定门面导入 | `backend/app/services/recommendation_service.py` | `recommend_fruits`、`__all__` | 代码事实 | 01、05 |
| 单水果评分 | 六项权重加反馈修正 | `backend/app/services/recommendation_core/fruit_evaluation.py` | `BASE_SCORE_WEIGHTS`、`calculate_base_score` | 代码事实 | 05 |
| 硬过滤 | inactive/forbidden 等先移除 | 同上 | `filter_eligible_fruits` | 代码事实 | 05 |
| 营养归一化 | 完整 active 库上的 P05/P95 0～1 演示指数 | 同上 | `normalize_nutrition_profiles` | 代码事实 | 02、05 |
| 组合评分 | 0.70/0.15/0.10/0.05 当前组合公式 | `backend/app/services/recommendation_core/pair_selection.py` | `PAIR_SCORE_WEIGHTS` | 代码事实 | 05 |
| 跨天冷却 | 三阶段放宽，excluded_pair 永不恢复 | 同上 | `select_recommendation_pair`、`_pair_is_legal` | 代码事实 | 04、05 |
| 推荐理由 | 来自真实贡献，2～4 条 | `backend/app/services/recommendation_core/reasons.py` | `_build_reasons` | 代码事实 | 05 |
| 领域类型 | 算法输入/输出 dataclass | `backend/app/services/recommendation_types.py` | `RecommendationUser`、`PairSelection` 等 | 代码事实 | 00、05 |
| 用户/Auth 绑定 | JWT sub 映射业务用户 | `backend/app/auth/dependencies.py` | `get_current_user` | 代码事实 | 01、glossary |
| JWT 合同 | issuer/audience/role/session/sub 校验并拒绝匿名 | `backend/app/auth/jwt_verifier.py` | `JwtVerifier.verify` | 代码事实 | 01 |
| 基础表 | 八张业务表和 FK/索引 | `backend/alembic/versions/0001_create_daily_fruit_tables.py` | `upgrade` | migration 事实 | 02、06 |
| RLS | 启用 RLS 并撤销浏览器直接权限 | `backend/alembic/versions/0002_secure_daily_fruit_tables.py` | `BUSINESS_TABLES`、`upgrade` | migration 事实 | 02、06 |
| V2 字段 | 水果身份、熟悉度、分数等 | `backend/alembic/versions/0005_recommendation_v2_data_model.py` | `upgrade/downgrade` | migration 事实 | 02、06 |
| 消费周期 | 2/4/7 且当前只保存 | `backend/alembic/versions/0006_user_consumption_horizon.py` | `upgrade` | migration 事实 | 02、06 |
| 购买条件 | market access 与 online purchase 只保存 | `backend/alembic/versions/0007_user_market_access.py` | `upgrade` | migration 事实 | 02、06 |
| 消费子类型 | 类型是父水果内档案，不扩张顶层候选 | `backend/alembic/versions/0012_fruit_selection_options.py` | `upgrade` | migration 事实 | 02、05、06 |
| 质地与历史快照 | 统一 texture 字段并冻结历史展示 | `backend/alembic/versions/0013_texture_preference_and_fruit_profile.py` | `upgrade` | migration 事实 | 02、05、06 |
| 离散偏好 | 分数仅 `-1/0/1/2/NULL`，意愿仅用于明确没吃过 | `backend/alembic/versions/0014_enforce_discrete_fruit_preferences.py` | precheck、CHECK | migration 事实 | 02、06 |
| 类型策略 | matching mode 与 score effect 由后端声明 | `backend/app/selection_option_policy.py` | `selection_matching_mode_for_code`、`selection_option_score_effect_for_code` | 代码事实 | 05 |
| 旧算法重放 | 从固定 Git revision 解包并执行旧核心 | `backend/app/services/texture_baseline_replay.py` | `replay_v1_source_revision` | 代码/测试事实 | 05、07 |
| 19 画像审计 | 反例、公式、排序变化与分布集中度 | `backend/app/services/texture_profile_report.py` | `build_audit_report` | 代码/测试事实 | 05、07 |
| Mapper 回归 | ORM graph 转换保留零值和可变输入 | `backend/tests/test_recommendation_mapper.py` | mapper tests | 测试事实 | 07 |
| 推荐规则回归 | 季节/过滤/评分/配对/理由 | `backend/tests/services/` | `test_*` | 测试事实 | 05、07 |
| 应用不变量 | 不二次重算、旧组合排除 | `backend/tests/test_recommendation_application_invariants.py` | named tests | 测试事实 | 04、07 |
| 配置隔离 | 测试 URL 不可指向 Supabase | `backend/app/config.py`、`backend/tests/test_database_config.py` | `_validate_database_url` | 配置事实/测试事实 | 06、07 |
| 分层为何有益 | 减少耦合、提高可测性 | 多个目录 | 架构解释 | 通用知识 | 01、glossary |

## 使用方式

如果某个结论无法在表中找到源文件和符号，不应直接写进其他章节。先重新搜索当前
工作区；如果代码已变化，标记教材失效并更新对应章节。
