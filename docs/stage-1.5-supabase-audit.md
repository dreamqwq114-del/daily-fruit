# 阶段 1.5：Supabase 连接与只读审计

审计日期：2026-07-31  
审计范围：`daily-fruit` 本地仓库与已连接的 Supabase 项目

数据库写入：0  
结论：**目标项目身份、空业务结构和安全警告已在 S2-08 写入前再次确认；S2-07 已完成，当前只允许向 project ref `frzbbpocyzlqxljsrsiw` 应用已提交的 `0001` 和 `0002`，仍禁止 seed 和范围外数据库修改。**

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
| S2-03 本地 Pydantic Schema | 已完成 | 提交 `fab7a89`，完整后端测试 61 项通过 |
| S2-04 初始化 Alembic 文件 | 已完成 | 提交 `f2e4a21` |
| S2-05 基础迁移 | 已完成 | 提交 `ddbc214` |
| S2-06 本地 PostgreSQL 验证 | 已完成 | 提交 `36c3e29`，upgrade/downgrade/check 成功 |
| S2-07 安全迁移 | 已完成 | 提交 `a3a417d`，本地 RLS/grants 实测通过 |
| S2-08 目标 Supabase 迁移 | 已完成 | `public.alembic_version=0002`，远端复核通过 |
| 写入 seed 或业务数据 | 不允许 | 先完成 S2-09 数据审查和 S2-10 本地幂等测试 |

阶段 1.5 的“项目身份未知”阻塞已经解除；基础结构和安全迁移已经落地，
seed 仍受数据审查和本地幂等测试门禁约束。

## 9. 下一步

Luna 的下一个任务应为 `S2-09：准备和验证演示数据文件`。该任务只创建
受控数据文件和静态验证测试，不连接数据库、不实现 seed 写入。

## 10. S2-08 迁移执行与复核（2026-07-31）

写入前再次确认：

- 连接器只返回 `Daily Fruit`；
- project ref 为 `frzbbpocyzlqxljsrsiw`；
- organization ref 为 `gacwsgimtxvfyoyokjqs`；
- `public` 用户表为 0，八个目标表均不存在；
- Supabase 迁移记录和 `public.alembic_version` 均不存在；
- `ensure_rls` 仍启用，原两项函数执行权限 WARN 仍存在。

执行方式：本机没有保存数据库密码，因此从已提交 Alembic migration
离线生成 SQL，经 Supabase migration 接口按两次事务应用；没有在
Dashboard 手写另一套 DDL，也没有写入 seed。

Supabase 迁移记录：

- `20260731102105_alembic_0001_create_daily_fruit_tables`；
- `20260731102133_alembic_0002_secure_daily_fruit_tables`。

执行后实际结果：

- `public.alembic_version = 0002`；
- 八张业务表全部存在且共 0 行；
- 8 个主键、9 个外键、8 个唯一约束、29 个 CHECK 约束；
- 业务表共有 22 个索引（含主键和唯一约束索引）；
- 八张业务表全部启用 RLS，policy 数为 0；
- `anon`、`authenticated` 对八张表的 CRUD 权限行数为 0；
- 两个角色对八个 identity sequence 的权限行数为 0；
- `PUBLIC`、`anon`、`authenticated` 均不能执行
  `public.rls_auto_enable()`；
- `ensure_rls` event trigger 仍启用；
- 重复/孤立业务记录为 0；
- 没有修改 `auth` 或 `storage` schema。

Security advisor 原两项 WARN 已消失。当前只有 9 条
`rls_enabled_no_policy` INFO，这是第一版刻意的 deny-by-default 状态；
不应通过添加宽泛 policy 消除。Performance advisor 的 5 条
`unused_index` INFO 来自刚创建且尚无业务查询的空表，不能作为删除
必要外键/历史查询索引的依据。

## 11. S2-11 seed 与最终审计（2026-07-31）

写入前第三次确认：连接器仍只返回 `Daily Fruit`，project ref 仍为
`frzbbpocyzlqxljsrsiw`，`public.alembic_version=0002`，水果、营养、
季节和所有行为表计数均为 0。

使用提交 `1174603` 的 seed 生成 UTF-8 PostgreSQL upsert SQL，校验只
包含 fruits、fruit_nutritions、fruit_seasons 三条 INSERT/ON CONFLICT，
再通过 Supabase SQL 接口作为单个事务执行。远端连续执行两次，第二次
没有增加行数。

最终远端结果：

- fruits：24；
- fruit_nutritions：24；
- fruit_seasons：48，其中跨年月份记录 10；
- 必需水果：22/22；
- users、user_fruit_preferences、recommendations、
  recommendation_items、recommendation_feedback：全部为 0；
- 重复自然键：0；
- 孤立记录：0；
- 非法分数、价格或月份记录：0；
- `public.alembic_version=0002`；
- 八张业务表 RLS：8/8 启用，policies：0；
- `anon`、`authenticated` 业务表 CRUD 权限：0；
- `PUBLIC`、`anon`、`authenticated` 对 `rls_auto_enable()` 的执行
  权限均为 false；
- `ensure_rls` event trigger 仍启用；
- Supabase 迁移记录仍只有已审查的 0001、0002；
- security advisor 只有 9 条预期 deny-by-default INFO；
- performance advisor 只有 5 条新空表的 unused-index INFO。

最终本地验收：

- 后端：82 passed；
- Alembic：`0002 (head)`，history 顺序正确，check 无新操作；
- 前端：`npm run build` 成功；
- 前端构建和 Git 受控文件秘密扫描无命中。

阶段二完成，当前不允许继续修改数据库或提前实现下一阶段功能。
