# 阶段四验收标准

## 分层与连接

- Router 不包含 SQLAlchemy 查询或推荐公式；
- Repository 不提交事务；
- 写 Service 明确提交一次，异常由 Session 依赖回滚；
- runtime Engine/连接池可复用，Session 每请求关闭；
- 纯推荐算法仍不依赖 ORM 或 Session；
- 所有关系响应在 Session 内构建，不触发 detached lazy load。

## API 功能

- 创建、获取和修改用户成功；
- 获取和完整替换水果偏好成功，未知 fruit ID 不产生部分写入；
- 获取水果列表和详情成功，inactive 不暴露；
- 首次获取今日推荐生成恰好两项；
- 重复获取返回同一 active 推荐；
- 换一组把旧组改为 replaced，refresh_number 递增并记录 change_requested；
- 有至少三种合格水果时，刷新不立即返回完全相同组合；
- 提交七种 feedback 成功，重复同类型幂等；
- 历史包含理由、反馈和 replaced 状态；
- 无效 user_id、fruit_id、item_id、无候选和无 active refresh 有明确状态码；
- 数据库异常只返回通用 `503`，不泄漏连接或 SQL 信息。

## 数据与性能

- 推荐响应包含 Fruit、Nutrition、Season、Reasons 和 Feedback 所需字段；
- 近期历史和反馈使用批量查询，没有循环内 SQL；
- 推荐详情使用 eager loading，没有 N+1；
- 历史返回数量有上限且无无界 OFFSET；
- 同用户同日并发获取最终只有一个 active 推荐；
- reasons JSONB 往返序列化后通过 Pydantic 契约。

## 验证

- Repository/Service 单元测试通过；
- FastAPI TestClient API 测试通过；
- 在精确名为 `daily_fruit_test` 的本地 PostgreSQL 上完成迁移、seed 和 API 集成测试；
- `python -m pytest -q` 成功；
- `alembic check`、`alembic current`、`alembic history` 成功；
- 前端 `npm run build` 仍成功；
- 没有新增迁移或远程 Supabase 写入；
- `.env` 未被跟踪，秘密扫描无真实凭据；
- Git working tree 干净。

## 2026-07-31 验收结果

- 后端全量：`165 passed`，包含纯算法、Schema、配置、迁移、安全、seed 和 API；
- FastAPI + 本地 PostgreSQL API 专项：`21 passed`；
- 并发 today 请求实测返回同一 recommendation ID，数据库只有一个 active；
- 已验证七种 feedback、重复反馈幂等、refresh 不同组合、change_requested 和历史响应；
- 已验证 today 与 history 查询次数上限，未发现逐 item 查询；
- `alembic current` 为 `0002 (head)`，`alembic history` 正常，`alembic check`
  返回 `No new upgrade operations detected`；
- `npm run build` 成功；
- Router 无 SQL/算法调用，Repository 无 commit，纯算法无 Session/SQLAlchemy 依赖；
- 受控文件未发现真实数据库 URL、Supabase secret、JWT 或被跟踪的 `.env`；
- 本阶段只修改本地代码和可丢弃 `daily_fruit_test`，没有远程 Supabase 写入；
- S4 验收通过，S5 Vue 页面尚未授权和实现。
