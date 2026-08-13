# 术语表

## 分层术语

**ORM model**：SQLAlchemy 将 Python class 映射到表和 relationship 的对象。当前
`User`、`Fruit`、`Recommendation` 属于 ORM；它们带 Session 状态，不能自动等于算法对象。

**Pydantic schema**：HTTP 输入/输出验证合同，如 `UserCreate`、`UserRead`、
`RecommendationDetail`。Schema 负责边界数据，不负责 SQL 查询。

**Domain object**：与持久化无关的算法数据合同。当前 `RecommendationUser`、
`RecommendationFruit`、`ScoredFruit`、`PairSelection` 是 dataclass。

**Repository**：封装数据库查询、预加载、锁和持久化操作的模块。它不应决定推荐分数。

**Application Service**：编排多个 Repository、Mapper、纯算法和事务的业务层。当前
`recommendation_application_service.py` 负责首次推荐、换组、历史和反馈。

**Facade**：稳定的对外门面。当前 `recommendation_service.py` 显式导出 core 函数，
并组装 `RecommendationResult`；外部业务不必依赖 core 内部模块。

## 事务与数据库术语

**Transaction**：一组原子数据库操作，要么全部 commit，要么 rollback。

**flush**：把当前 Session 的待写操作发送到数据库，可能取得 identity ID；不会结束事务。

**commit**：提交事务，使修改对其它事务可见。

**rollback**：撤销当前事务未提交的修改。刷新流程依靠它恢复旧 active。

**advisory lock**：PostgreSQL 提供的应用自定义锁。当前按用户和事务获取，防并发生成
同日 active；它不是表行数据本身。

**migration**：数据库结构演进脚本。`revision/down_revision` 组成历史链；不能把 ORM
当前状态当作完整历史。

**seed**：将演示数据幂等导入数据库的脚本。它不是 migration，也不应在测试或教学中随意
写生产数据。

**eager loading**：查询时主动加载 relationship。当前 Repository 使用 `selectinload`
降低推荐加载阶段的 N+1 风险。

**N+1 query**：先查 1 个列表，再对列表中的 N 个对象各查一次关系，导致大量查询。

## 推荐术语

**hard constraint**：违反后候选被移除，不能靠更高分恢复，例如 forbidden、inactive、
`excluded_pair`。

**soft score**：不直接排除候选，只改变排序，如口味、季节、价格、便利性、历史和反馈。

**fallback**：主数据缺失或主路径不可用时的保守替代逻辑。当前 feedback 有聚合 fallback，
但 fallback 不是把未知伪装成喜欢。

**deterministic random**：给定同一输入和 seed 得到可复现的随机选择。当前只在 near-top
组合中选择，不是安全随机数。

**idempotency**：重复执行同一操作不会产生额外不一致。当前反馈由
`(recommendation_item_id, user_id, feedback_type)` 唯一约束和 service 检查共同保护。

**characterization baseline**：在重构前冻结同一输入下的可观察行为。可靠基线必须能
追溯并执行对应源版本；JSON 自称来自某个 commit 不是充分证据。

## 相似对象对比

| 对象 A | 对象 B | 关键区别 |
| --- | --- | --- |
| `User` | `RecommendationUser` | ORM 持久化图 vs 算法输入快照 |
| `Fruit` | `RecommendationFruit` | SQLAlchemy relationship/Decimal vs 纯领域字段 |
| `RecommendationFruit` | `ScoredFruit` | 原始输入 vs 已计算子分数和 base score |
| `PairSelection` | `RecommendationResult` | 算法内部 pair 选择 vs Facade 对外结果/理由 |
| `Recommendation` | `RecommendationItem` | 一组推荐的生命周期 vs 其中一个水果 |
| `RecommendationItem` | `Feedback` | 展示记录 vs 用户事件 |

## 历史、反馈与冷却

- `history_events`：带业务日期的展示/食用事件；`feedback_events`：带时间和类型的反馈事件。
- `recent_fruit_ids`：兼容旧的水果 ID 集合；`history_events` 能表达日期和次数，优先级更具体。
- `previous_pairs`：较长窗口的组合新颖度；`cooldown_pairs`：短期完整组合硬冷却。
- `excluded_pair`：本次换组的上一组，永远不能恢复；它不是普通历史降分。
- `has_tried=None`：未知；`has_tried=False`：明确没吃过；不能把 NULL 批量写成 false。
- `preference_score`：显式喜欢/不喜欢程度；`is_forbidden`：禁止推荐，优先级更高。
- 当前 `preference_score` 只允许 `-1/0/1/2` 或 `NULL`；`2` 表示特别喜欢并要求已吃过。
- `selection matching mode` 决定怎样选父水果内类型；`score effect` 决定类型是否改变评分，
  两者不是同一个概念。
- `eaten`：一次反馈事件，不等于永久 liked；`unavailable`：供应/购买问题，不等于口味 dislike。
- `change_requested`：换组事件，不自动转化为水果长期负反馈。

## 并发术语的适用边界

**pessimistic concurrency** 可以用于解释当前的 `for_update=True` 和 advisory lock：
先锁住资源再执行临界区。**optimistic concurrency** 在当前仓库没有明确的版本列、
ETag 或冲突重试合同，因此只能作为未来设计概念，不能说项目已经实现。

## 最后提醒

当前权重、冷却天数、三级放宽顺序、0～1 演示营养指数和水果数量都是项目启发式参数。
它们不是行业标准、概率、医学分数或机器学习模型。
