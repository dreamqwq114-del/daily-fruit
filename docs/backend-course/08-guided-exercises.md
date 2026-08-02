# 引导练习

## 使用规则

练习默认只读，不连接远程数据库、不执行 migration/seed。除非题目明确允许，
不要修改生产代码。每题列出学习目标、难度、源码入口和是否需要运行代码。

## 基础练习

### B1：画函数输入输出

- **目标**：读懂 Python 类型合同。
- **难度**：基础。
- **阅读**：`backend/app/services/recommendation_types.py` 的 `RecommendationFruit`、
  `ScoredFruit`。
- **任务**：写出 `RecommendationFruit → ScoredFruit` 新增了哪些字段。
- **运行**：否；可用文本阅读。
- **修改生产代码**：不允许。

### B2：区分三种对象

- **目标**：区分 ORM、Schema、领域对象。
- **难度**：基础。
- **阅读**：`backend/app/models/user.py`、`backend/app/schemas/user.py`、
  `backend/app/services/recommendation_mapper.py`。
- **任务**：说明 `User`、`UserRead`、`RecommendationUser` 的用途和生命周期。
- **运行**：否。
- **修改生产代码**：不允许。

### B3：写只读 SQL

- **目标**：练习 SELECT/JOIN。
- **难度**：基础。
- **阅读**：`backend/alembic/versions/0001_create_daily_fruit_tables.py`。
- **任务**：写一条查询某个虚构 `user_id=1` 的 recommendation item 与 fruit name 的
  `SELECT`。标注“只读示例；请勿在生产库执行”。
- **运行**：否；SQL 只提交文本。
- **修改生产代码**：不允许。

### B4：flush 与 commit

- **目标**：理解事务阶段。
- **难度**：基础。
- **阅读**：`backend/app/database.py`、`recommendation_repository.py` 的写方法。
- **任务**：解释为什么 `_persist_recommendation` 后先 flush、最后由 service commit。
- **运行**：否。
- **修改生产代码**：不允许。

### B5：找到 Facade 内部实现

- **目标**：理解稳定导入路径。
- **难度**：基础。
- **阅读**：`recommendation_service.py` 和 `recommendation_core/`。
- **任务**：从 `recommend_fruits` 找到 pair 选择和理由生成函数。
- **运行**：否。
- **修改生产代码**：不允许。

## 中级练习

### M1：追踪今日推荐

- **目标**：建立完整调用链。
- **难度**：中级。
- **阅读**：`routers/recommendations.py`、Application Service、Mapper、Repository。
- **任务**：分别写出“已有 active”和“没有 active”的调用链，并标注数据库访问点。
- **运行**：可选，运行安全的推荐 service 测试。
- **修改生产代码**：不允许。

### M2：硬约束还是软评分

- **目标**：区分过滤和排序。
- **难度**：中级。
- **阅读**：`fruit_evaluation.filter_eligible_fruits`、`pair_selection._pair_is_legal`。
- **任务**：把 inactive、forbidden、季节、价格、历史和 excluded_pair 分类。
- **运行**：否。
- **修改生产代码**：不允许。

### M3：`has_tried` 三态

- **目标**：理解 NULL 语义。
- **难度**：中级。
- **阅读**：`models/user.py`、`schemas/user.py`、`test_recommendation_v2.py`。
- **任务**：解释 `None`、`False`、`True` 在 discovery level 0/1/2 下的差别。
- **运行**：可选，运行过滤测试。
- **修改生产代码**：不允许。

### M4：手算单水果分

- **目标**：理解加权分而非概率。
- **难度**：中级。
- **阅读**：`fruit_evaluation.BASE_SCORE_WEIGHTS`、`calculate_base_score`。
- **任务**：使用六个子分数和一个反馈调整计算简化 base score，说明 clamp 的位置。
- **运行**：否；手算即可。
- **修改生产代码**：不允许。

### M5：判断冷却恢复阶段

- **目标**：理解三级放宽。
- **难度**：中级。
- **阅读**：`pair_selection.select_recommendation_pair`。
- **任务**：给定昨日水果、`cooldown_pairs` 和 `excluded_pair`，判断某 pair 在哪一阶段
  可能恢复，以及哪一组永远不能恢复。
- **运行**：可选，运行 pair tests。
- **修改生产代码**：不允许。

### M6：为什么需要 Mapper

- **目标**：理解边界转换。
- **难度**：中级。
- **阅读**：`recommendation_mapper.py`。
- **任务**：指出 mapper 对 Decimal、缺失营养和供应状态做了哪些语义处理。
- **运行**：否。
- **修改生产代码**：不允许。

## 高级练习

### A1：刷新失败回滚测试

- **目标**：验证事务一致性。
- **难度**：高级。
- **阅读**：`recommendation_application_service.py`、
  `test_recommendation_application_invariants.py`。
- **任务**：设计一个测试：核心抛出异常后，原 active 仍为 active，且没有新 active。
- **运行**：可在安全测试环境运行已有测试；不写远程库。
- **修改生产代码**：只允许在独立测试分支练习，不改本仓库。

### A2：设计新字段 migration

- **目标**：理解 schema 演进。
- **难度**：高级。
- **阅读**：`0005`、`0006`、`0007`、对应 ORM/schema/mapper/tests。
- **任务**：为一个虚构字段设计 upgrade、downgrade、默认值、CHECK、API 和回归测试清单。
- **运行**：否；不要创建 migration 文件。
- **修改生产代码**：不允许。

### A3：分析 N+1

- **目标**：识别 ORM 查询性能风险。
- **难度**：高级。
- **阅读**：`fruit_repository.py`、`recommendation_repository.py`。
- **任务**：指出去掉 `selectinload` 后可能产生的查询，并提出不改变业务语义的验证方式。
- **运行**：否。
- **修改生产代码**：不允许。

### A4：设计推荐指标

- **目标**：把启发式系统连接到评估。
- **难度**：高级。
- **阅读**：`test_fixed_profiles_v2.py`、`test_reasons.py`。
- **任务**：设计重复率、覆盖率、反馈接受率三个离线/线上指标，说明分母和时间窗口。
- **运行**：否。
- **修改生产代码**：不允许。

### A5：不污染长期偏好的反馈

- **目标**：区分事件与偏好。
- **难度**：高级。
- **阅读**：`recommendation_application_service.submit_feedback`、
  `fruit_evaluation._feedback_adjustment`。
- **任务**：解释 `unavailable`、`expensive`、`change_requested` 为什么不能直接写成
  `preference_score=-1`。
- **运行**：否。
- **修改生产代码**：不允许。

### A6：ORM 与 migration 冲突分析

- **目标**：建立事实优先级。
- **难度**：高级。
- **阅读**：`models/`、全部 `alembic/versions/`、`test_model_metadata.py`。
- **任务**：列出发现冲突后的停止条件、证据和最小修复计划；不要自行选择一方。
- **运行**：可运行静态测试，但不要连接远程数据库。
- **修改生产代码**：不允许。

## 本章事实来源

| 教学结论 | 源文件 | 事实类型 |
| --- | --- | --- |
| 练习入口来自当前服务边界 | `backend/app/services/` | 代码事实 |
| migration 练习基于真实 revision | `backend/alembic/versions/` | migration 事实 |
| 测试练习引用真实行为保护 | `backend/tests/` | 测试事实 |`n