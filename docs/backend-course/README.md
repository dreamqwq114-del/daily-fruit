# Daily Fruit 后端源码导读

## 教学材料定位

这是一套基于当前 `daily-fruit` 工作区的源码导读材料。它不重建后端，
也不是新的规范层，而是帮助学习者从一次 HTTP 请求追踪到数据库事务和
纯推荐算法。文中的“当前项目实现”只表示代码、migration 或测试直接支持
的事实；“通用知识”是 Python、PostgreSQL、SQLAlchemy 或测试的普遍概念；
“设计取舍”解释本项目的选择；“可改进方向”表示尚未实现的想法。

## 适合读者

- 已掌握 Python 基础、SQL 基础、class、函数和类型标注；
- 想理解 FastAPI、Pydantic、SQLAlchemy、PostgreSQL、Alembic 和 pytest 的协作；
- 容易在跨文件调用、ORM 对象与领域对象转换、事务边界之间迷失的学习者。

主要学习 Python 后端、数据库和推荐核心；Vue 只作为集成上下文阅读。

如果目前只完成了 IOM103 Python/SQL 基础，先走
[IOM103、SQL 与 Daily Fruit 衔接路线](../learning-path/README.md)，补齐类型合同、
pytest 工程测试、PostgreSQL、SQLAlchemy 与 Alembic，再进入本源码课。

## 推荐学习顺序

1. [学习地图](00-learning-map.md)：建立目录和对象演进的全局图；
2. [架构与调用链](01-architecture-and-call-chain.md)：跟踪一次请求；
3. [数据库模型](02-database-model.md) 与 [Repository](03-sqlalchemy-and-repositories.md)；
4. [Application Service 与事务](04-application-service-and-transactions.md)；
5. [推荐引擎](05-recommendation-engine.md)；
6. [Alembic](06-alembic-migrations.md) 与 [测试](07-testing-and-debugging.md)；
7. 完成 [练习](08-guided-exercises.md)，再对照 [答案](solutions/08-guided-exercises-solutions.md)；
8. 用 [源码地图](10-source-map.md) 和 [术语表](glossary.md) 复查。

## 事实与维护说明

本教材基于生成时的当前工作区。代码、完整 Alembic migration 链和测试始终
是事实来源，教学文档不能反向覆盖代码事实。推荐模块、ORM、migration、事务
流程或领域类型变化后，对应章节必须重新审计。若工作区存在未提交修改，单独
的 commit hash 不能完整表示教材快照；维护者应重新记录 `git status` 和实际
源码版本。仓库事实与旧文档冲突时，教材应标记冲突，而不是猜测。

## 项目范围与个人贡献

教材讲解整个项目的集成结构，不代表学习者独立实现了所有模块。根据当前项目
说明，学习者主要设计、审计和维护 Python 推荐算法与数据库部分；FastAPI 路由、
认证和前端主要作为集成上下文阅读。无法从仓库确认具体作者的代码，不应在简历
或面试中认领为个人独立实现。

## 如何使用

每章优先按函数名、类名和相对路径定位源码，而不是依赖可能漂移的行号。例如：

```text
backend/app/services/recommendation_application_service.py
  get_today_recommendation
  refresh_recommendation
  _calculate_recommendation
```

SQL 示例默认只读；若是简化示例，会明确标记“不可直接执行”。不要为了练习
直接连接生产 Supabase、执行 migration 或写入 seed。

## 章节状态

本目录中的章节按源码导读方式编写，包含真实入口、调用链、混淆点、练习和事实
来源表。参数、冷却天数、演示营养指数和权重都只是当前项目的启发式实现，不是
行业标准，也不是机器学习模型的训练结果。

本轮教材已核对到 migration `0014`。当前偏好分是离散的 `-1/0/1/2` 或 `NULL`，
`willing_to_try` 只允许出现在 `has_tried=False` 的记录上；水果子类型还带有明确的
匹配模式和分数作用。远程 Supabase 的实际 head 不由教材推断，执行前仍需现场核对。

## 个人贡献边界提醒

阅读整套材料可以理解完整工程，但“读懂”不等于“实现”。面试回答应区分：项目
使用的技术环境、学习者主要负责的推荐算法和数据库工作、以及为理解集成流程而
阅读的 API 和前端代码。

## 目录

- [00-learning-map](00-learning-map.md)
- [01-architecture-and-call-chain](01-architecture-and-call-chain.md)
- [02-database-model](02-database-model.md)
- [03-sqlalchemy-and-repositories](03-sqlalchemy-and-repositories.md)
- [04-application-service-and-transactions](04-application-service-and-transactions.md)
- [05-recommendation-engine](05-recommendation-engine.md)
- [06-alembic-migrations](06-alembic-migrations.md)
- [07-testing-and-debugging](07-testing-and-debugging.md)
- [08-guided-exercises](08-guided-exercises.md) / [solutions](solutions/08-guided-exercises-solutions.md)
- [09-interview-questions](09-interview-questions.md)
- [10-source-map](10-source-map.md)
- [glossary](glossary.md)
