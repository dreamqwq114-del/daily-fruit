# Luna：阶段二小任务列表

## 执行总则

- 一次只执行一个任务，完成验收并等待确认后才能进入下一个；
- 每次开始前读取 `AGENTS.md`、阶段 1.5 审计和阶段二设计；
- 不得为了“完成阶段”一次性实现全部内容；
- 目标 Supabase project ref 未确认时，所有数据库写入任务禁用；
- 发现范围外文件、未知表、真实数据或身份不一致时立即停止。

## S2-00：恢复目标项目可见性并完成只读门禁

目标：确认 `daily-fruit` 目标 project ref，并补全只读审计。

允许修改：

- `docs/stage-1.5-supabase-audit.md`

禁止：

- 修改任何 Python/Vue 文件；
- 创建 Alembic；
- 执行 SQL；
- 迁移、seed、policy 或 grants 修改；
- 读取或修改其他 Supabase 项目。

执行：

```text
Supabase: list_projects
Supabase: get_project(用户确认的 project ref)
Supabase: list_tables(public, verbose)
Supabase: list_migrations
Supabase: list_extensions
Supabase: get_advisors(security)
Supabase: get_advisors(performance)
```

只有目标身份确认后，才可使用只读 SQL补充约束、索引、RLS、policies、grants 和行数审计。

验收：

- 项目名称、ref、组织与用户确认一致；
- 八类远端结构证据完整；
- 冲突风险明确；
- 文档给出“允许/不允许进入 S2-01”。

停止条件：

- 项目列表仍为空；
- ref 不一致；
- 出现多个无法区分的候选项目；
- 需要任何写操作才能继续。

## S2-01：定义数据库配置合同

目标：只完善配置和连接工厂边界，不创建 Model。

允许修改：

- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/tests/test_database_config.py`
- `README.md` 中的配置说明

禁止：

- Models、Schemas、Repositories、API；
- Alembic；
- 远端数据库连接测试；
- 写入任何真实 URL。

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

验收：

- 支持 runtime、migration、test URL；
- 正式环境禁止 debug；
- 测试 URL 防误连 Supabase 正式域名；
- 连接错误不泄漏；
- 现有 health 测试仍通过。

停止条件：

- 需要真实密码才能通过测试；
- 测试尝试连接远端项目；
- 配置变化破坏 `/health`。

## S2-02：创建 SQLAlchemy metadata 和 ORM Model

目标：仅在 Python metadata 中定义八张表。

允许修改：

- `backend/app/models/__init__.py`
- `backend/app/models/base.py`
- `backend/app/models/user.py`
- `backend/app/models/fruit.py`
- `backend/app/models/recommendation.py`
- `backend/tests/test_model_metadata.py`

禁止：

- Pydantic Schema；
- Router、Service、Repository；
- Alembic 文件；
- 连接或修改 Supabase；
- seed。

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_model_metadata.py -q
```

验收：

- 八张表均存在于 metadata；
- 类型、nullable、CHECK、unique、FK、delete rule 和索引与设计文档一致；
- 没有建表行为；
- 测试只检查 metadata。

停止条件：

- 远端审计发现设计冲突；
- 需要修改未授权表名；
- ORM 无法表达目标约束且没有先汇报。

## S2-03：创建数据库 Pydantic Schema

目标：定义数据库输入输出验证，不实现 API。

允许修改：

- `backend/app/schemas/`
- `backend/tests/test_schemas.py`

禁止：

- Router；
- Service/算法；
- Repository；
- 数据库连接；
- Alembic、seed。

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_schemas.py -q
```

验收：

- 分数、月份、价格、status、feedback type 范围验证；
- reasons 固定结构且稳定序列化；
- ORM Schema 与 API Schema 不混在 Model 文件中。

停止条件：

- Schema 字段与已批准设计不一致；
- 为通过测试放宽校验。

## S2-04：初始化 Alembic，仅连接测试库

目标：创建 Alembic 目录和安全配置，不生成业务迁移。

允许修改：

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/.gitkeep`
- `backend/tests/test_alembic_config.py`

禁止：

- 生成表迁移；
- `alembic upgrade` 远端；
- 在 `alembic.ini` 写 URL；
- Supabase 写操作。

运行：

```powershell
cd backend
alembic --help
alembic history
.\.venv\Scripts\python.exe -m pytest tests/test_alembic_config.py -q
```

验收：

- URL 从安全配置注入；
- metadata 可加载；
- 未配置测试/迁移 URL 时安全失败；
- versions 中没有业务 migration。

停止条件：

- Alembic 尝试读取正式 URL；
- URL 被写入受控文件。

## S2-05：生成并静态审查基础表迁移

目标：生成 `0001`，但不应用 Supabase。

允许修改：

- `backend/alembic/versions/*_create_daily_fruit_tables.py`
- `backend/tests/test_migration_static.py`

禁止：

- RLS/policies/grants；
- seed；
- 远端 upgrade；
- `IF NOT EXISTS` 掩盖冲突；
- DROP 未知对象。

运行：

```powershell
cd backend
alembic revision --autogenerate -m "create daily fruit tables"
.\.venv\Scripts\python.exe -m pytest tests/test_migration_static.py -q
```

验收：

- upgrade/downgrade 与 metadata 一致；
- 只包含八张目标表及批准对象；
- 人工审查生成 SQL；
- 没有系统 schema 变化。

停止条件：

- autogenerate 识别到远端未知对象；
- migration 出现意外 DROP/ALTER。

## S2-06：在可丢弃 PostgreSQL 验证 `0001`

目标：只在 `daily_fruit_test` 数据库验证 upgrade/downgrade。

允许修改：

- `backend/tests/integration/test_migrations.py`
- 必要的测试 fixture

禁止：

- Supabase 正式库；
- SQLite；
- 修改 migration 以外的业务功能；
- seed。

运行：

```powershell
cd backend
alembic upgrade head
alembic downgrade -1
alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests/integration/test_migrations.py -q
```

验收：

- 三次 Alembic 命令均成功；
- 约束和删除策略实测；
- ORM 与测试库 schema 一致。

停止条件：

- 数据库名不满足测试保护；
- URL 包含正式 Supabase host；
- downgrade 涉及非测试数据。

## S2-07：创建并静态审查安全迁移

目标：准备 `0002` RLS/grants，但不应用 Supabase。

允许修改：

- `backend/alembic/versions/*_secure_daily_fruit_tables.py`
- `backend/tests/test_security_migration_static.py`
- 安全文档勘误

禁止：

- 宽泛 allow policy；
- 修改 auth/storage；
- 远端执行；
- service role key。

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_security_migration_static.py -q
```

验收：

- 八表启用 RLS；
- anon/authenticated deny-by-default；
- grants/revokes 显式；
- downgrade 只恢复本迁移管理的状态。

停止条件：

- 无法确认远端默认 privileges；
- migration 会影响非 daily-fruit 表。

## S2-08：经明确批准后迁移目标 Supabase

目标：只应用已审查的 `0001` 和 `0002`。

允许修改：

- 迁移执行记录；
- `docs/stage-1.5-supabase-audit.md` 的验证结果

禁止：

- 临时手写 Dashboard DDL；
- seed；
- 任何未提交迁移；
- 其他项目。

运行：

```powershell
cd backend
alembic current
alembic history
alembic upgrade head
```

验收：

- 执行前再次显示并核对 project ref；
- upgrade 成功；
- 重新读取实际表、约束、索引、RLS、policies、grants；
- advisors 无未解释高风险项。

停止条件：

- project ref 变化；
- migration current 不符合预期；
- 出现未知数据或对象冲突；
- 任一 SQL 失败。

## S2-09：准备演示数据文件

目标：只创建数据文件和静态校验。

允许修改：

- `data/fruits_seed.json`
- `data/nutrition_demo.csv`
- `data/seasons_demo.csv`
- `backend/tests/test_seed_files.py`
- README 数据免责声明

禁止：

- seed 脚本；
- 数据库连接；
- 推荐算法；
- 权威医学声明。

运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_seed_files.py -q
```

验收：

- 20 到 30 种水果；
- 必需水果齐全；
- 自然键无重复；
- 数值范围和月份合法；
- 数据口径与免责声明一致。

停止条件：

- 数据来源无法说明为演示；
- 混用真实单位与归一化分数。

## S2-10：实现幂等 seed，并仅在测试库验证

目标：实现 dry-run、事务和 upsert。

允许修改：

- `backend/app/seed/`
- `backend/tests/integration/test_seed_idempotency.py`

禁止：

- 远端 Supabase seed；
- 删除已有行；
- 用户、推荐或反馈数据；
- API 和推荐算法。

运行：

```powershell
cd backend
python -m app.seed.seed_fruits --dry-run
python -m app.seed.seed_fruits
python -m app.seed.seed_fruits
.\.venv\Scripts\python.exe -m pytest tests/integration/test_seed_idempotency.py -q
```

验收：

- 两次执行行数不增加；
- 失败整体 rollback；
- 无重复自然键；
- dry-run 无写入。

停止条件：

- 测试 URL 指向正式库；
- upsert 会覆盖非 seed 管理的数据；
- 出现 delete/truncate。

## S2-11：经明确批准后写入演示 seed 并最终审计

目标：在已确认的目标项目写入演示目录数据并只读复核。

允许修改：

- 审计文档中的最终计数和结果

禁止：

- 用户行为数据；
- 重复执行以外的临时 SQL；
- 其他项目；
- 未经确认扩大数据集。

验收：

- project ref 再次核对；
- seed 第一次和第二次均成功；
- 第二次行数不增加；
- 无重复、无孤立记录；
- Supabase schema、迁移、RLS、grants、advisors 最终复核完成；
- Git 无秘密。

停止条件：

- 任一计数异常；
- 出现未知真实数据覆盖风险；
- advisors 出现新的高风险项。

## Luna 的第一个任务

必须从 **S2-00** 开始。当前不得执行 S2-01 或任何数据库实现任务。

