# 面试问题与参考回答

以下回答只描述仓库能支持的事实。参考回答不应说“我独立实现了整个前后端系统”；
应区分项目技术环境、个人主要负责的 Python 推荐算法/数据库工作，以及为理解集成
流程而阅读的 API/前端部分。

## Python 后端

### 1. 为什么推荐核心使用 dataclass，而不是 ORM？

- **基础回答**：dataclass 表达纯内存领域合同；ORM 还包含数据库状态和 relationship。
- **深挖**：如果算法访问 ORM 会怎样？
- **项目参考**：`recommendation_mapper.py` 把 `User/Fruit` 转成 `RecommendationUser/Fruit`，
  核心不持有 Session。
- **常见错误**：说 dataclass 自动提供数据库持久化。

### 2. `None` 和 `False` 为什么不能混用？

- **基础回答**：`None` 是未知，`False` 是明确否定。
- **深挖**：它影响哪两个推荐规则？
- **项目参考**：`has_tried=None` 不等于没吃过；过滤和组合合法性只对明确 `False` 执行对应规则。
- **边界**：这是当前字段语义，不是所有产品都必须使用三态。

## SQLAlchemy 与 PostgreSQL

### 3. flush 与 commit 的区别？

- **基础回答**：flush 把 SQL 发出并可能取得 ID；commit 才结束事务。
- **项目参考**：Repository 写入 flush，Application Service 在推荐图成功后 commit，失败可 rollback。
- **追问**：为什么 add_recommendation 不应自己 commit？因为刷新需要把旧状态、新主表、items 作为一个事务。

### 4. partial unique index 防什么？

- **参考回答**：`recommendations` 对 `status='active'` 的 `(user_id, recommendation_date)` 做唯一约束，
  防同日两个 active；用户级 advisory lock 解决流程竞争，两者作用不同。
- **常见错误**：说它保证了算法只会返回最优水果。

### 5. 为什么使用 eager loading？

- **参考回答**：水果 Repository 用 `selectinload` 预加载营养和季节，推荐详情批量加载 item/fruit/feedback，
  避免评分或响应序列化阶段出现 N+1。
- **深挖**：需结合查询计数或日志验证，不应只凭感觉。

## 事务与 Alembic

### 6. 换组失败后如何保证旧推荐仍 active？

- **参考回答**：旧 active 变更只 flush 不 commit；核心错误让外层 Session rollback，旧记录状态恢复，
  新记录不持久化。
- **代码入口**：`refresh_recommendation`、`_calculate_recommendation`、应用不变量测试。

### 7. 为什么不能直接在 Dashboard 改表？

- **参考回答**：Dashboard 改动无法表达完整 revision/down_revision 历史，其他环境和部署无法重放；应先写
  Alembic、ORM、schema 和测试，并在确认目标环境后执行。
- **边界**：紧急 SQL 可能有例外，但必须同步可审计 migration。

## 推荐算法

### 8. 当前系统是不是机器学习？

- **参考回答**：不是。当前是白盒规则系统：硬过滤、人工权重、历史/反馈衰减、完整组合枚举和 seeded 选择。
- **常见错误**：把 0～1 分数说成概率或准确率。

### 9. 为什么不直接取 base score 前两名？

- **参考回答**：当前 `select_recommendation_pair` 枚举全部合法 pair，加入营养互补、感官类别差异和组合新颖度，
  所以第二个水果可能不是单水果第二名。
- **深挖**：`excluded_pair` 是硬约束；near-top seed 只在接近最高 pair 分的集合中选择。

### 10. 哪些字段当前没有进入算法？

- **参考回答**：`market_access_level`、`accepts_online_purchase`、`consumption_horizon_days` 由资料 API 保存，
  但 `user_to_recommendation_input` 不映射到 `RecommendationUser`，当前不参与排序。
- **改进方向**：定义语义、数据来源、权重和回归测试后再接入。

## 测试与架构

### 11. monkeypatch 应该 patch 哪里？

- **参考回答**：patch 被测模块实际查找的名字。应用测试 patch
  `app.services.recommendation_application_service.recommend_fruits`，因为该模块已经导入了本地名称。
- **常见错误**：只 patch 定义函数的原始模块。

### 12. 你如何验证行为保持？

- **参考回答**：固定画像、日期、历史、反馈和 random seed，逐字段比较水果 ID、分数、理由和 contribution；
  再跑服务、应用、API 和安全 migration 测试。
- **个人边界**：如果实际工作主要是算法和数据库，应明确说 API/前端是集成阅读范围。

## 项目复盘

### 13. 当前设计的主要限制？

- 演示水果、季节、价格和营养数据不是实时或医学数据；
- 权重和冷却参数是启发式，缺少大规模用户实验；
- 购买条件和消费周期还未参与排序；
- Auth、RLS、部署环境变化需要持续审计。

### 14. 你会如何改进？

先建立推荐重复率、覆盖率和反馈接受率基线，再考虑可获得性、库存、快过期和真实
反馈；任何新字段先完成 migration/mapper/算法合同和回归测试。不要为了“更复杂”直接
引入神经网络或 LLM。

## 参考源码

`backend/app/services/recommendation_application_service.py`、
`backend/app/services/recommendation_core/`、`backend/app/services/recommendation_mapper.py`、
`backend/tests/` 和 `backend/alembic/versions/`。`n