# 阶段 1.5：Supabase 连接与只读审计

审计日期：2026-07-31  
审计范围：`daily-fruit` 本地仓库与已连接的 Supabase 项目

数据库写入：0  
结论：**目标项目身份和空业务结构已经确认；S2-02 已完成，允许准备 S2-03 Pydantic Schema，但远端迁移前必须先处理并复核现有安全警告。**

## 1. 本地仓库状态

本轮复核时：

- Git 分支：`main`；
- 审计前 HEAD：`6c79f6d docs: record Supabase audit gate and stage-two design`；
- 审计前工作树：干净；
- 阶段一基础提交：`a33b35e chore: add stage-one daily fruit skeleton`；
- 未读取或修改 `daily-fruit` 以外的项目；
- 未创建 ORM、Alembic、业务表、seed、推荐算法或正式页面。

此前已经检查：

- 受控文件和 Git 历史中没有发现 `.env`、数据库密码、Supabase secret/service role key 或完整数据库连接串；
- `backend/.env` 不存在且被 `.gitignore` 忽略；
- `backend/.env.example` 的 `DATABASE_URL` 为空；
- 前端没有 Supabase 高权限凭据；
- 当前配置使用后端环境变量和 `postgresql+psycopg://`，可以支持后续连接 Supabase PostgreSQL；
- `/health?check_database=true` 只做安全的连通性检查，不泄漏连接信息。

## 2. 目标 Supabase 项目

连接器当前只返回一个项目，且名称与用户配置的目标一致，因此本轮将其确认为 `daily-fruit` 的目标项目：

| 项目 | 值 |
|---|---|
| 名称 | `Daily Fruit` |
| Project ref | `frzbbpocyzlqxljsrsiw` |
| Organization ref | `gacwsgimtxvfyoyokjqs` |
| Region | `ap-northeast-1` |
| 状态 | `ACTIVE_HEALTHY` |
| PostgreSQL 主版本 | 17 |
| 数据库版本 | `17.6.1.155` |
| 创建时间 | `2026-07-31T07:38:38.15377Z` |

没有在文档中记录数据库密码、连接串或任何 secret。

## 3. `public` schema 结构

由于连接器的表列表接口两次出现传输错误，本轮使用只读系统目录 `SELECT` 交叉验证，未执行任何 DDL 或 DML。

### 表、字段、约束和索引

| 审计项 | 结果 |
|---|---|
| `public` 普通表/分区表 | 0 |
| `public` 字段 | 0 |
| 主键、外键、唯一与 CHECK 约束 | 0 |
| 用户索引 | 0 |
| RLS policies | 0 |
| 表级 grants | 0 |
| `public.alembic_version` | 不存在 |
| 业务数据或测试数据 | 不存在 |

计划中的八张表均不存在，因此目前没有表名或字段冲突：

- `users`
- `fruits`
- `fruit_nutritions`
- `fruit_seasons`
- `user_fruit_preferences`
- `recommendations`
- `recommendation_items`
- `recommendation_feedback`

### 已有函数和事件触发器

`public` 并非字面意义上的空 schema，已有：

- 函数：`public.rls_auto_enable()`；
- 函数所有者：`postgres`；
- 属性：`SECURITY DEFINER`；
- 用途：在 `public` 中创建表、`CREATE TABLE AS` 或 `SELECT INTO` 后自动执行 `ENABLE ROW LEVEL SECURITY`；
- 事件触发器：`ensure_rls`；
- 触发时机：`ddl_command_end`；
- 状态：启用。

还存在 Supabase 管理的系统事件触发器，例如 PostgREST、GraphQL、Cron 和网络扩展相关触发器。本项目不得修改这些系统对象。

## 4. 迁移和扩展

### 迁移记录

- Supabase 连接器返回的项目迁移列表为空；
- `public` 中没有 `alembic_version`；
- 只发现 Supabase 系统 schema 自己的迁移表：
  - `auth.schema_migrations`
  - `realtime.schema_migrations`
  - `storage.migrations`

这些系统迁移表不属于 `daily-fruit`，不得复用或修改。

### 已安装扩展

| 扩展 | Schema | 版本 |
|---|---|---|
| `pgcrypto` | `extensions` | `1.3` |
| `pg_stat_statements` | `extensions` | `1.11` |
| `supabase_vault` | `vault` | `0.3.1` |
| `uuid-ossp` | `extensions` | `1.1` |
| `plpgsql` | `pg_catalog` | `1.0` |

当前阶段不需要新增、升级或移动扩展。

## 5. RLS、权限和安全顾问

### RLS 和 policies

- 当前没有业务表，因此不存在可报告的表级 RLS 状态或 policy；
- `ensure_rls` 会在后续创建 `public` 表时自动启用 RLS；
- 自动启用 RLS 不等于已经定义可用且安全的 policies；
- 第一版浏览器只调用 FastAPI，不能依赖浏览器直接访问业务表。

### Schema 和函数权限

- `PUBLIC`、`anon`、`authenticated`、`service_role` 和 `postgres` 对 `public` schema 有 `USAGE`；
- `anon` 和 `authenticated` 没有 `CREATE`；
- `public.rls_auto_enable()` 当前使用默认函数 ACL，`PUBLIC` 可执行；
- 实测 `anon` 和 `authenticated` 均可执行该函数。

### 默认对象权限

`public` 的默认权限取决于对象创建者：

- `postgres` 创建的表默认向 `anon`、`authenticated` 和 `service_role` 授予部分非 CRUD 表权限；
- `supabase_admin` 创建的表、序列和函数默认向上述 API 角色授予更宽权限；
- 因此不能依赖平台默认 ACL。阶段二迁移必须显式撤销 `anon` 和 `authenticated` 对业务表、序列和业务函数的权限，再逐对象验证实际 grants。

### Advisors

Security advisor 返回两项 `WARN`：

1. `anon_security_definer_function_executable`：`anon` 可执行 `public.rls_auto_enable()`；
2. `authenticated_security_definer_function_executable`：`authenticated` 可执行同一 `SECURITY DEFINER` 函数。

Performance advisor：没有发现问题。

参考：

- [Anon security-definer function executable](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable)
- [Authenticated security-definer function executable](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable)

本轮没有撤销权限、修改函数、修改 event trigger 或执行其他安全变更。修复必须先形成可审查的 Alembic 迁移方案，并确认不会破坏 Supabase 的自动 RLS 机制。

## 6. 冲突和数据风险

- 没有现存业务表、业务约束、索引或数据需要兼容；
- 没有发现计划表名冲突；
- 没有发现孤立业务记录，因为业务表尚不存在；
- `auth`、`storage`、`realtime` 等 Supabase 系统 schema 已存在，必须保持不变；
- 主要风险不是数据覆盖，而是默认权限和现有 `SECURITY DEFINER` 函数暴露；
- 迁移使用的数据库角色会改变新对象的默认 ACL，必须在迁移后读取实际权限，不能只审查迁移文本。

## 7. 本轮实际执行

只执行了以下只读操作：

- 列出和读取目标项目元数据；
- 读取 `public` relations、columns、constraints、indexes、policies 和 grants；
- 读取函数、事件触发器和函数 ACL；
- 读取 schema 权限和默认权限；
- 读取扩展；
- 读取 Supabase 迁移列表，并检查迁移表；
- 运行 security 和 performance advisors。

明确未执行：

- `CREATE`
- `ALTER`
- `DROP`
- `INSERT`
- `UPDATE`
- `DELETE`
- `TRUNCATE`
- migration
- seed
- policy/grant 修改

## 8. 阶段二准入判定

分项判定：

| 工作 | 是否允许 | 条件 |
|---|---|---|
| S2-01 本地配置契约和连接保护 | 已完成 | 提交 `742eeeb`，17 项后端测试通过 |
| S2-02 本地 ORM metadata | 已完成 | 提交 `ae83235`，完整后端测试 28 项通过 |
| S2-03 本地 Pydantic Schema | 允许 | 只定义和测试 Schema，不连接数据库 |
| 初始化 Alembic 文件 | 暂缓 | 按任务列表逐项执行 |
| 对 Supabase 执行迁移 | 不允许 | 先批准安全修复方案并复核实际 grants/RLS |
| 写入 seed 或业务数据 | 不允许 | 迁移、结构复核和幂等 seed 测试通过后再批准 |

阶段 1.5 的“项目身份未知”阻塞已经解除；数据库实施仍受安全警告和逐任务审批约束。

## 9. 下一步

Luna 的下一个任务应为 `S2-03：创建数据库 Pydantic Schema`：

- 只修改 `backend/app/schemas/` 和 `backend/tests/test_schemas.py`；
- 验证分数、月份、价格、status、feedback type 和 reasons 结构；
- 保持 SQLAlchemy Model 与 Pydantic Schema 分离；
- 不创建 Repository、Service 或 Router；
- 不初始化 Alembic；
- 不连接本地或远端数据库；
- 不执行 SQL、迁移或 seed；
- 完成后运行指定测试并独立提交。

在任何远端数据库写入任务之前，还应单独准备一个可审查的安全迁移设计，说明如何最小范围撤销 `public.rls_auto_enable()` 对 `PUBLIC`、`anon`、`authenticated` 的执行权限，并验证 `ensure_rls` 仍能由数据库事件触发器正常工作。
