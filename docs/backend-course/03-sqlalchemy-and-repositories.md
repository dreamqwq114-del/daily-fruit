# SQLAlchemy 与 Repository

## 学习目标

理解 ORM model、Session 和 Repository 的关系，能从真实方法判断查询是否预加载、
什么时候 flush/commit，以及如何识别 N+1 风险。

## 业务问题

推荐算法需要一份完整但脱离数据库的快照：水果、营养、季节、偏好、历史和反馈。
Repository 负责把这个快照高效地取出来；它不决定“哪个水果更好”。

## Session 生命周期

`backend/app/database.py` 的 `get_database_session` 创建 Session，交给 FastAPI
依赖使用，请求结束关闭；请求异常时先 rollback。`get_runtime_session_factory`
设置 `autoflush=False`、`expire_on_commit=False`，因此 service 明确控制写入时机。

- `execute/select`：读取或执行 SQL；
- `add`：把对象放入当前 Unit of Work；
- `flush`：把待写 SQL 发给数据库，通常用于取得 identity ID，但事务仍未提交；
- `commit`：提交整个事务；
- `rollback`：撤销本事务中尚未提交的改动。

这些是通用 SQLAlchemy 概念；当前项目选择由 Application Service 调用 commit，而
Repository 的写方法只负责 add/flush。

## 两个真实 Repository 案例

### 案例一：批量加载水果

`backend/app/repositories/fruit_repository.py` 的 `list_active_fruits` 使用
`selectinload(Fruit.nutrition)` 和 `selectinload(Fruit.seasons)`。这会在有限的
批量查询中加载关系，避免算法循环里访问 `fruit.nutrition` 时一水果一查询。
它只返回 `is_active` 水果；是否合乎用户偏好由推荐核心判断。

### 案例二：取得 active 推荐

`recommendation_repository.get_active_recommendation` 按用户和业务日期查询 status
为 `active` 的记录，完整详情方法使用预加载的 item、fruit、nutrition、seasons 和
feedback。`for_update=True` 只在刷新路径使用，用于配合用户级 advisory lock。

其它重要方法包括：`next_refresh_number`、`history_events`、`feedback_events`、
`previous_pairs`、`add_recommendation`、`get_item` 和 `add_feedback`。

## ORM 与领域对象

ORM `User` 有 relationship 和 SQLAlchemy 状态，不能直接传给纯算法。Mapper 的
`user_to_recommendation_input`、`fruit_to_recommendation_input` 把 Decimal、缺失值、
季节和偏好转换成 `RecommendationUser/Fruit`。这样推荐核心可以在没有 Session 的
情况下测试，也不会在评分时偷偷查询数据库。

## N+1 识别

危险写法是：先查询水果，再在 Python 循环中访问一个未预加载的 relationship。
当前 Repository 使用 `selectinload`，这是代码事实；是否所有未来查询都保持这个
性质，应由测试和 SQL 日志继续验证。不要因为只有 24 种演示水果就忽略生产查询模式。

## 常见错误修改

- 在 Repository 中写“如果用户喜欢就加 0.2”这样的业务规则；
- 在 `add_recommendation` 中 commit，导致两条 item 与主表无法作为一个事务图回滚；
- 在 `get_item` 查到 item 后不校验 `item.recommendation.user_id`；
- 直接把 ORM relationship 传给算法，产生隐式 lazy load。

## 小练习

阅读 `fruit_repository.list_active_fruits` 和 `recommendation_repository.add_recommendation`，
分别回答：哪一个负责预加载？哪一个负责 flush？如果第二个方法也 commit，会给
`refresh_recommendation` 的失败回滚带来什么变化？

## 本章事实来源

| 教学结论 | 源文件 | 符号 | 事实类型 |
| --- | --- | --- | --- |
| Session 依赖回滚并关闭 | `backend/app/database.py` | `get_database_session` | 代码事实 |
| 水果关系批量预加载 | `backend/app/repositories/fruit_repository.py` | `list_active_fruits` | 代码事实 |
| 推荐详情预加载 | `backend/app/repositories/recommendation_repository.py` | `get_active_recommendation`、`get_recommendation` | 代码事实 |
| Repository 写入只 flush | `recommendation_repository.py` | `add_recommendation`、`add_feedback` | 代码事实 |
| ORM 与算法对象分离 | `backend/app/services/recommendation_mapper.py` | 两个 mapper | 代码事实 |

## 本章总结

Repository 是数据库查询边界，不是业务规则仓库；Session 是事务上下文，不是每个
函数都可以随意提交的全局对象。预加载和明确的 flush/commit 让调用链可解释。`n