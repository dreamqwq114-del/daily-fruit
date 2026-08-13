# 架构与调用链

## 学习目标

理解 Router、Schema、Application Service、Mapper、Repository、ORM、Facade
和 Pure Recommendation Core 的边界，并能追踪一次“今日推荐”请求。

## 业务问题

用户只想得到两种水果，但后端需要同时处理认证、用户资料、季节、历史、反馈、
事务和持久化。把所有逻辑写在路由中会难以测试，也会让数据库细节污染算法。

## 涉及的真实源码

- `backend/app/routers/recommendations.py`：HTTP 路由；
- `backend/app/auth/dependencies.py`：从 JWT 得到当前业务用户；
- `backend/app/services/recommendation_application_service.py`：业务编排；
- `backend/app/repositories/recommendation_repository.py`：查询、锁和写入；
- `backend/app/services/recommendation_mapper.py`：ORM → 领域对象；
- `backend/app/services/recommendation_service.py`：稳定算法 Facade；
- `backend/app/services/recommendation_core/`：纯推荐模块。

## 主调用链

| 阶段 | 输入对象 | 调用函数 | 输出对象 | 是否访问数据库 | 下一层 |
| --- | --- | --- | --- | --- | --- |
| HTTP | JSON/Authorization | Router 函数 | FastAPI 参数 | 间接 | 认证/Session 依赖 |
| 身份 | Bearer JWT | `get_current_principal`、`get_current_user` | `AuthPrincipal`、`User` | 是，按 `auth_user_id` 查询 | Application Service |
| 编排 | `Session`、`user_id` | `get_today_recommendation` | `RecommendationDetail` | 是 | Repository/Mapper |
| 加载 | ORM 图 | `list_active_fruits`、历史/反馈查询 | ORM 对象集合 | 是 | Mapper |
| 转换 | `User`、`Fruit` | `user_to_recommendation_input`、`fruit_to_recommendation_input` | `RecommendationUser/Fruit` | 否 | Facade |
| 算法 | 领域对象 | `recommend_fruits` | `RecommendationResult` | 否 | 持久化 |
| 持久化 | 领域结果 | `_persist_recommendation` | `Recommendation` | 是 | commit/响应 |
| 响应 | ORM 推荐图 | `recommendation_to_detail` | `RecommendationDetail` | 否 | HTTP JSON |

## 核心概念

**Router** 处理路径、状态码和依赖注入；不写评分公式。**Schema** 是外部 HTTP
输入/输出的验证合同。**Application Service** 组织跨 Repository 的业务流程和
事务。**Repository** 负责 SQLAlchemy 查询和持久化。**Mapper** 把数据库快照转成
不依赖数据库的算法输入。**Facade** 保持外部导入稳定；**Pure Core** 只接收内存
对象，因此可以不连接数据库运行单元测试。

## 为什么这样设计

- 核心不访问数据库：同一输入可以复现，测试不需要启动 PostgreSQL；
- Application Service 不重写评分公式：刷新、首次推荐和未来 API 共享同一个算法；
- Repository 不负责推荐规则：查询窗口和 SQL 优化不会偷偷改变评分语义；
- Facade 隔离内部拆分：外部代码继续从 `recommendation_service` 导入公开函数。

这些是当前项目的设计取舍，不是唯一正确的后端分层方式。

## 容易混淆的地方

1. `User` 和 `RecommendationUser` 不是同一个类：前者带 ORM relationship，后者
   是算法所需的不可持久化数据合同。
2. `RecommendationResult.total_score` 是组合分；每个
   `RecommendationItemResult.score` 是单水果 base score。
3. `get_today_recommendation` 可能直接复用 active 记录，所以“调用接口”不等于
   “每次都调用推荐算法”。
4. JWT 验证只确认身份；`get_current_user` 还要把 Supabase `sub` 映射到
   `public.users`，资料不存在时返回资源错误。

## 源码导读

从路由向下阅读：`get_today_recommendation` →
`recommendation_application_service.get_today_recommendation` →
`_calculate_recommendation` → `build_recommendation_context` →
`recommend_fruits`。算法返回后再读 `_persist_recommendation` 和
`_load_detail`，这样可以看到领域对象如何重新回到 ORM。

## 常见错误修改

- 在 Router 中直接 `session.execute` 并复制推荐公式；
- 把 `user_id` 放进请求体后信任客户端，而不使用 JWT 当前用户；
- 让 Facade 通过 `from ... import *` 隐藏公开合同；
- 为了省查询删除 `selectinload`，然后在评分循环里触发 N+1 查询。

## 小练习

画出 `GET /api/recommendations/today` 的八个节点，并在每条箭头上标注“ORM”或
“领域对象”。再找出一个节点，如果删除它会导致数据库细节泄漏到算法。

## 本章事实来源

| 教学结论 | 源文件 | 符号 | 事实类型 |
| --- | --- | --- | --- |
| Router 只编排 HTTP 依赖 | `backend/app/routers/recommendations.py` | 路由函数 | 代码事实 |
| JWT 身份映射业务用户 | `backend/app/auth/dependencies.py` | `get_current_user` | 代码事实 |
| ORM 转算法对象 | `backend/app/services/recommendation_mapper.py` | 两个 mapper | 代码事实 |
| 算法不持有 Session | `backend/app/services/recommendation_service.py` | `recommend_fruits` | 代码事实 |

## 本章总结

分层不是为了增加文件数量，而是为了让每个边界有单一责任：HTTP、事务、查询、
对象转换和纯算法可以分别测试、审计和演进。
