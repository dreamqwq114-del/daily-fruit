# 冷知识数据模型与展示审计

审计范围：`fruit_facts` migration、ORM、seed、推荐响应映射和 `FruitCard.vue`。本审计为实现后的独立只读复核，未修改代码或数据库。

## 结果

- 目标 Supabase 项目已确认，`public.alembic_version` 为 `0008`。
- `public.fruit_facts` 实际存在 72 行，覆盖 24 种水果，每种 3 条，`sort_order` 为 1/2/3。
- `(fruit_id, sort_order)` 重复组为 0；榴莲的 `botany`、`growth`、`aroma` 三条数据均存在且 active。
- 实际字段、主键、外键、`ON DELETE CASCADE`、唯一约束、3 个 CHECK 约束和 `(fruit_id, is_active)` 索引与 ORM/0008 migration 一致。
- RLS 已启用；`fruit_facts` 没有浏览器策略，`anon`、`authenticated` 和 `PUBLIC` 没有表或序列权限，后端数据库角色可访问。
- seed 使用 `(fruit_id, sort_order)` upsert，不执行 DELETE/TRUNCATE；生产写入需要 `--migration`、`DAILY_FRUIT_ALLOW_MIGRATION_SEED=yes` 和 `MIGRATION_DATABASE_URL`，默认模式仍只允许本地测试库。
- 推荐查询通过 `selectinload(Fruit.facts)` 预加载；`daily_fact` 按水果 `code` 与推荐日期确定性选择，同日稳定、日期变化轮换，不进入过滤、评分、营养互补或排序。
- 前端仅在 `item.daily_fact` 存在时显示“每日冷知识”，位置为水果简介之后、建议份量之前；缺失字段会隐藏提示块，没有榴莲硬编码。
- `recommendation_core`、推荐权重、用户偏好、历史数据和其他表未被修改。

## 验证记录

- 后端：`202 passed, 30 skipped`；跳过项是未配置可丢弃 `TEST_DATABASE_URL` 的数据库集成测试。
- API 测试已增加 `daily_fact` 响应断言；在配置测试数据库时会随推荐接口流程执行。
- 前端：23 个 unit tests、30 个 component tests 通过。
- 构建：`npm run build` 成功，构建产物包含“每日冷知识”文案。
- Alembic：`alembic current` 为 `0008 (head)`，`alembic history` 显示 `0007 -> 0008`。

## 非阻断风险

1. 当前环境没有测试 PostgreSQL，因此 API 集成断言未在本地数据库上执行；部署前应在隔离测试库补跑。
2. seed guard 通过 Supabase 主机名保护目标，不能从连接串本身证明 project ref；运行生产 seed 前仍需人工确认连接串属于 Daily Fruit 项目。
3. Supabase security advisor 对无 policy 的 RLS 表会给出提示，这是当前 backend-direct-only 设计的预期状态；若未来开放 Data API，应单独设计最小 RLS policy。
4. `source_note` 随 API 返回但前端不展示。若后续审核备注不应公开，可在下一阶段拆分内部/公开 schema。

结论：未发现 P0/P1 阻断问题，可以进入后端部署和线上 API 验证阶段；当前工作区尚未执行 Git commit 或 push。
