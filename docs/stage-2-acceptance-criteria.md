# 阶段二验收标准

阶段二只有在 `docs/stage-1.5-supabase-audit.md` 的门禁解除后才能实施。

## 1. 进入条件

- [x] 用户已确认连接器中的唯一 `Daily Fruit` 目标项目；
- [x] 连接器列出的项目与 project ref、名称和组织一致；
- [x] 已完成 `public` 表、约束、索引、迁移、RLS、policies、grants、扩展和 advisors 的只读审计；
- [x] 已确认八个计划表名不存在未解决冲突；
- [x] 已通过 S2-01 区分 runtime、migration、test 数据库 URL；
- [x] 用户批准当前唯一的小任务。

任一项不满足，停止数据库修改。

以上已勾选项目以 `3d71816` 和 `742eeeb` 的审计、代码及测试结果为
依据；执行远端写入前仍须重新核对 project ref 和实际数据库状态。

## 2. 仓库与秘密

- [x] `git status --short` 只包含当前任务允许的文件；
- [x] `backend/.env` 未被 Git 跟踪；
- [x] 工作树和 Git 历史中没有数据库密码、secret key、service role key 或完整凭据 URL；
- [x] 前端构建产物中没有数据库连接信息；
- [x] `.env.example` 只有空值或安全示例；
- [x] 未修改 `daily-fruit` 以外的文件。

验证：

```powershell
git status --short
git ls-files backend/.env
git grep -n "DATABASE_URL"
```

秘密扫描不得把匹配值打印到共享日志。

## 3. 配置与连接

- [x] SQLAlchemy 配置只接受 `postgresql+psycopg://`；
- [x] 运行时、迁移和测试连接可分别配置且不互相回退；
- [ ] Session Pooler/direct connection 的选择与部署网络一致；
- [x] 连接失败只返回稳定的公开错误，不返回 host、username、password 或 SQL；
- [ ] Session 在请求结束后关闭；
- [ ] 事务异常会 rollback；
- [x] 正式环境不允许 `DEBUG=true`；
- [x] 测试 URL 拒绝 `*.supabase.co` 和
  `*.pooler.supabase.com`，且数据库名必须包含 `daily_fruit_test`；
- [x] Supabase runtime/migration URL 要求安全 SSL mode，并拒绝端口
  `6543` 的 Transaction Pooler。

## 4. ORM 与 Schema

- [x] SQLAlchemy Model 位于独立的 `app/models/`，不包含 Pydantic Schema；
- [ ] Router 不包含推荐算法或 SQLAlchemy 查询；
- [ ] Repository 负责查询；
- [ ] Service 负责编排、验证和事务；
- [x] SQLAlchemy metadata 包含八张目标表；
- [x] ORM 类型、nullable、默认值、约束和外键与设计文档一致；
- [x] `recommendation_items.reasons` 使用 JSONB；
- [x] reasons 的 Pydantic 结构可稳定序列化。

## 5. Alembic

在可丢弃 PostgreSQL 测试库执行：

```powershell
alembic upgrade head
alembic current
alembic history
alembic downgrade -1
alembic upgrade head
```

验收：

- [x] `alembic upgrade head` 成功；
- [x] `alembic current` 指向 head；
- [x] `alembic history` 顺序清晰；
- [x] `alembic downgrade -1` 成功；
- [x] downgrade 后再次 upgrade 成功；
- [x] `alembic_version` 与实际结构一致；
- [x] 迁移不依赖静默 `IF NOT EXISTS` 掩盖冲突；
- [x] 迁移中没有真实密码或 project ref 硬编码；
- [x] 没有修改 `auth`、`storage` 系统对象。

## 6. 约束与外键

- [x] 所有 0 到 1 分数拒绝范围外数值；
- [x] `price_level` 只允许 1 到 3；
- [x] 月份只允许 1 到 12；
- [x] 营养值拒绝负数；
- [x] `preference_score` 只允许 -1 到 2；
- [x] feedback type 只允许定义值；
- [x] recommendation status 只允许 `active`、`replaced`；
- [x] 同一用户同一天 refresh_number 唯一；
- [x] 同一用户同一天最多一个 active 推荐；
- [x] 同一推荐 rank 唯一且只允许 1、2；
- [x] 同一推荐不能包含重复 fruit_id；
- [x] 删除 Recommendation 会级联删除 Items；
- [x] 删除 Item 会级联删除 Feedback；
- [x] 有历史 Item 的 Fruit 无法被删除；
- [x] 有历史 Recommendation 的 User 无法被删除；
- [x] 没有孤立外键记录。

## 7. 索引

- [x] 每个常用外键方向都有可用索引；
- [x] 用户推荐历史查询使用 `(user_id, recommendation_date DESC, refresh_number DESC)`；
- [x] active 推荐使用部分唯一索引；
- [x] 地区季节查询使用以 `region` 开头的索引；
- [x] 索引没有与唯一约束无意义重复；
- [x] performance advisor 没有未解释的高优先级问题。

## 8. RLS 与权限

- [x] 八张业务表 RLS 状态已读取并与设计一致；
- [x] 第一版 `anon`、`authenticated` 不能通过 Data API 访问业务表；
- [x] 没有宽泛 `USING (true)` policy；
- [x] 没有把 `TO authenticated` 误当作行级所有权控制；
- [x] 没有依赖 `user_metadata` 做授权；
- [x] grants 与 RLS 在同一安全迁移中审查；
- [x] security advisor 没有未解释的高优先级问题；
- [x] FastAPI 使用的数据库权限和绕过 RLS 风险已记录。

## 9. Seed

在测试数据库至少连续执行两次：

```powershell
python -m app.seed.seed_fruits --dry-run
python -m app.seed.seed_fruits
python -m app.seed.seed_fruits
```

验收：

- [x] 20 到 30 种水果写入成功；
- [x] 必需水果全部存在；
- [x] 第二次执行不增加水果、营养或季节行数；
- [x] `fruits.name` 无重复；
- [x] 每个 fruit 最多一条 nutrition；
- [x] seasons 联合唯一键无重复；
- [x] seed 不创建推荐、反馈或真实用户行为数据；
- [x] seed 失败时整体回滚；
- [x] 演示数据免责声明存在；
- [x] 没有声称数据是权威医学数据。

## 10. 测试与最终核对

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
```

- [x] 后端测试全通过；
- [x] 前端生产构建成功；
- [x] 数据库错误不会向客户端泄漏；
- [x] 迁移后重新读取 Supabase 实际 schema；
- [x] ORM 与实际 Supabase schema 一致；
- [x] 读取迁移记录、RLS、policies、grants 和 advisors；
- [x] 重复/孤立记录查询返回 0；
- [x] Git 工作树只包含预期变更；
- [x] 用户确认结果后才提交或进入下一任务。

## 11. 停止条件

出现以下任一情况立即停止：

- project ref 与用户确认值不一致；
- 发现同名未知表或真实数据；
- 迁移包含 DROP、TRUNCATE 或不可逆类型转换；
- 测试 URL 指向正式 Supabase；
- downgrade 会删除非测试数据；
- migration、ORM 和实际 schema 不一致；
- RLS/grants 使匿名角色获得意外访问；
- 任何秘密将进入 Git 或日志；
- 无法解释的数据库或权限错误重复出现。
