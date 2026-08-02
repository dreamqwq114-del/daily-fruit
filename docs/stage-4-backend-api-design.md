# 阶段四：后端 API 设计

## 1. 范围

S4 完成 FastAPI 业务接口、Repository、事务型应用 Service、ORM 到算法输入的转换和
TestClient 集成测试。Vue 正式页面、Supabase Auth 和远程数据库写入不在本阶段。

本阶段复用 `0001`、`0002` 和既有 seed，不新增表、字段、索引、迁移或 RLS policy。

## 2. 分层

```text
Router -> Application Service -> Repository -> SQLAlchemy Session
                         |
                         -> recommendation_service.py Facade
                              -> recommendation_core (pure algorithm)
```

- Router：HTTP 输入、状态码、依赖注入和响应模型；
- Application Service：业务规则、事务提交/回滚、推荐生成与刷新编排；
- Repository：SQLAlchemy 查询、锁和持久化；
- 纯推荐算法：由 `recommendation_service.py` Facade 调用
  `recommendation_core`，只接收内存对象，不持有 Session；
- Schema：HTTP 请求与响应，不放数据库查询。

## 3. 数据库连接和事务

- FastAPI 是持久化后端：IPv6 可用时使用 Direct Connection；IPv4 环境使用
  Supavisor Session Pooler 5432；不使用 Transaction Pooler 6543；
- SQLAlchemy runtime engine 在进程内复用连接池，不为每个请求创建 Engine；
- 每个请求获得独立 Session，依赖退出时关闭；异常时回滚；
- 写 Service 只在业务成功后提交一次；外部 HTTP 调用不放入事务；
- “今日推荐”和“换一组”在事务内使用按 `user_id` 的
  `pg_advisory_xact_lock`，避免并发生成两个 active 推荐；
- 数据库异常统一返回不含 SQL、URL、密码和内部异常文本的 `503`。

## 4. Repository 查询策略

- 水果详情使用 `selectinload` 一次性加载 nutrition 和 seasons；
- 推荐详情批量加载 items、fruit、nutrition、seasons 和 feedback，禁止逐项查询；
- 用户偏好通过 `user_id` 联合唯一索引前缀读取；
- 今日 active 推荐使用既有 partial unique index；
- 历史使用既有 `(user_id, recommendation_date desc, refresh_number desc)` 索引，
  只返回有上限的最新记录，不使用无界 OFFSET；
- 近期水果和反馈使用 JOIN/批量查询，不在循环中查询；
- 不为低基数且仅 24 条演示数据的 `fruits.is_active` 单独增加索引。

## 5. API

| 方法 | 路径 | 成功状态 | 行为 |
|---|---|---:|---|
| POST | `/api/users` | 201 | 创建演示用户 |
| GET | `/api/users/{user_id}` | 200 | 获取用户 |
| PUT | `/api/users/{user_id}` | 200 | 部分更新非空字段 |
| GET | `/api/users/{user_id}/fruit-preferences` | 200 | 获取偏好 |
| PUT | `/api/users/{user_id}/fruit-preferences` | 200 | 用完整列表替换当前偏好 |
| GET | `/api/fruits` | 200 | 获取 active 水果 |
| GET | `/api/fruits/{fruit_id}` | 200 | 获取 active 水果详情 |
| GET | `/api/recommendations/today?user_id=1` | 200 | 返回已有 active；没有时生成并保存 |
| POST | `/api/recommendations/refresh` | 201 | 替换 active，递增 refresh_number |
| GET | `/api/users/{user_id}/recommendations` | 200 | 返回最近历史，默认最多 30 组 |
| POST | `/api/recommendations/items/{item_id}/feedback` | 201/200 | 首次创建；重复同类型幂等返回 |

不存在资源统一返回 `404`；候选不足或没有可刷新的 active 推荐返回 `409`；请求字段非法
返回 FastAPI/Pydantic `422`。

## 6. 今日推荐

1. 获取事务级用户 advisory lock；
2. 验证用户存在；
3. 再查询当天 active 推荐；存在则直接返回，不重新计算；
4. 批量加载 active 水果、用户偏好、近期推荐和历史反馈；
5. 转换为 S3 内存输入，使用用户、日期和 refresh_number 生成稳定 random seed；
6. 执行纯算法并保存 recommendation 与两条 items；
7. 提交后重新批量读取完整响应。

日期统一按 `APP_TIMEZONE`，默认 `Asia/Shanghai`，避免服务器 UTC 日期越界。

## 7. 换一组

1. 获取同一 advisory lock；
2. 锁定当天 active 推荐；没有 active 时返回 `409`；
3. 把旧组状态设为 `replaced`；
4. 在旧组 rank 1 item 上幂等记录 `change_requested`；
5. `refresh_number = 当天最大值 + 1`；
6. 把旧组水果放在近期历史最前；
7. 若算法仍返回完全相同组合且至少有第三个合格候选，尝试排除旧组中的一项重新选择；
8. 保存新 active 推荐并一次提交。

数据库 partial unique index仍是最终并发保护。

## 8. 偏好和反馈

- `PUT fruit-preferences` 采用完整替换语义；空列表表示清空当前偏好；
- 提交前一次性验证所有 fruit ID 存在，避免部分写入；
- feedback 的 user_id 从 recommendation item 所属推荐推导，第一版不信任客户端传入；
- 同一用户、item、feedback_type 重复提交幂等返回已有记录；
- 第一版固定 ID/localStorage 机制不是生产认证，正式 Auth 接入前不得对公网开放写接口。

## 9. 安全与 Supabase

- Vue 仍不持有数据库 URL、secret 或 service role key；
- FastAPI 使用 PostgreSQL URL，RLS 对 `anon`/`authenticated` 继续 deny-by-default；
- 本阶段不创建 Data API grants，不修改 `auth`、`storage`、`realtime`；
- 2026-07-31 Supabase changelog 中与本阶段最相关的变化是新表不再自动暴露给
  Data API；本项目不依赖 Data API，因此无需调整；
- extension version pinning、Management API logs 和 self-hosted gateway 变化不影响 S4。

## 10. 实现审查结论

- runtime Engine 进程内复用，Session 每请求关闭且异常回滚；
- 同用户推荐使用 transaction advisory lock，并由 partial unique index双重保护；
- today 页面刷新只读取已保存 active 推荐；
- refresh 在同一短事务内完成 replaced、change_requested 和新 active 写入；
- 水果、推荐 items、营养、季节与 feedback 使用 select-in eager loading；
- API 测试实测 today 和 history 查询数量有固定上限，不随 item 数量线性增长；
- 所有 API 响应在 Session 可用时转换为 Pydantic Schema，不依赖 detached lazy load；
- 第一版 user_id 机制已明确标记为非生产认证方案。

## 11. 官方资料核对

- [Supabase Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres)
  用于确认 Direct、Session Pooler 和 Transaction Pooler 的用途；
- [Supabase Query Optimization](https://supabase.com/docs/guides/database/query-optimization)
  用于复核 JOIN、过滤和排序列的索引策略；
- [Supabase Changelog](https://supabase.com/changelog)
  已在实现前检查 2026-07-31 前的 breaking changes，没有需要 S4 改变架构的条目。
