# Luna：阶段四小任务列表

## 总则

- 一次只执行一个任务，通过测试并提交后再进入下一项；
- 所有数据库集成测试仅使用精确名为 `daily_fruit_test` 的本地 PostgreSQL；
- 禁止连接或写入远程 Supabase，禁止新增 migration；
- 不提前实现 Vue 正式页面或 Supabase Auth；
- 发现需要 schema 变化、未知表或真实数据时立即停止。

## S4-00：冻结 API 和事务合同

允许修改：S4 三份文档和 `AGENTS.md`。

验收：接口、状态码、事务、并发、失败方式和阶段边界明确。

## S4-01：Session 生命周期和统一错误

允许修改：

- `backend/app/database.py`
- `backend/app/errors.py`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/.env.example`
- 对应测试

禁止：业务 Router、Repository 和算法改动。

验收：Engine 复用、Session 关闭/回滚、时区配置和安全 503 均有测试。

## S4-02：Repository 与 ORM 转换

允许修改：

- `backend/app/repositories/`
- `backend/app/services/recommendation_mapper.py`
- 对应测试

禁止：Router、事务提交、迁移。

验收：用户、水果、偏好、推荐、历史和反馈查询齐全；关系批量预加载。

## S4-03：用户、偏好和水果 API

允许修改：

- `backend/app/services/user_service.py`
- `backend/app/services/fruit_service.py`
- `backend/app/routers/users.py`
- `backend/app/routers/fruits.py`
- 必要 Schema、main 注册和测试

验收：六个接口、404、422、完整替换事务和 inactive 过滤通过。

## S4-04：推荐事务 Service

允许修改：

- `backend/app/services/recommendation_application_service.py`
- 必要 Repository、Schema 和测试

禁止：Router、前端和 schema migration。

验收：today 幂等、refresh 替换、稳定 seed、不同组合、change_requested、feedback
幂等和历史组装通过。

## S4-05：推荐 Router 与 PostgreSQL API 集成测试

允许修改：

- `backend/app/routers/recommendations.py`
- `backend/app/main.py`
- `backend/tests/api/`
- `backend/tests/integration/test_api.py`

验收：全部业务接口由 TestClient 在本地 PostgreSQL 贯通，数据库错误不泄漏。

## S4-06：完整审查

允许修改：README、AGENTS、S4 文档和审查发现的范围内缺陷。

验收：全量测试、Alembic 检查、前端构建、秘密扫描和 Git 状态全部通过。

## 当前下一任务

- `S4-00` 已完成；
- 当前下一任务为 `S4-01`：Session 生命周期和统一错误。
