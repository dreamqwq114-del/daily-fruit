# 阶段 1.5：Supabase 连接与只读审计

审计日期：2026-07-31  
审计范围：`daily-fruit` 本地仓库与当前 Supabase 连接器  
数据库写入：0  
结论：**目标项目未确认，不允许进入会修改数据库的阶段二任务。**

## 1. 本地仓库状态

审计时：

- Git 分支：`main`；
- HEAD：`fd22be9 chore: use public npm registry for Sites`；
- 工作树：干净；
- 阶段一基础提交：`a33b35e chore: add stage-one daily fruit skeleton`；
- 后续还有两次 Sites 部署支持提交：
  - `dc55755 chore: add Sites deployment support`；
  - `fd22be9 chore: use public npm registry for Sites`。

因此，当前仓库不能被描述为“仅包含 `a33b35e`”。Sites 文件是前端部署支持，不是 Supabase 配置，也没有改变数据库边界。

### 已读取的主要文件

- `README.md`
- `docs/stage-1-plan.md`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/.env.example`
- `backend/requirements.txt`
- `backend/tests/test_health.py`
- `frontend/src/App.vue`
- `frontend/.openai/hosting.json`
- `.gitignore`
- Git 状态、受控文件列表与最近提交

未读取、未修改 `daily-fruit` 以外的项目。

## 2. 本地安全检查

### 结果

- 受控文件中没有 `.env`；
- 本地只有 `backend/.env.example`，其 `DATABASE_URL` 为空；
- `backend/.env` 当前不存在，并且已被 `.gitignore` 忽略；
- 工作树扫描未发现：
  - 带用户名和密码的 PostgreSQL URL；
  - `sb_secret_...`；
  - `sbp_...`；
  - JWT 形态的 Supabase key；
- 全部 Git 提交历史扫描也未发现上述凭据形态；
- 未发现 `SUPABASE_URL`、`SUPABASE_KEY`、`service_role` 值或 `*.supabase.co` 项目 URL；
- 未发现 `.mcp.json`、本地 `supabase/` 目录或 `supabase/config.toml`；
- `frontend/.openai/hosting.json` 是 Sites 部署元数据，只包含 Sites project ID 和空的 D1/R2 绑定，不是 Supabase project ref 或数据库凭据。

### 配置代码评估

当前后端已经具备连接 Supabase PostgreSQL 的最小技术基础：

- `DATABASE_URL` 从 `backend/.env` 或进程环境读取；
- SQLAlchemy 版本为 2.0；
- 使用 psycopg 3；
- `postgresql+psycopg://...` 可交给 `create_engine()`；
- `/health?check_database=true` 只执行 `SELECT 1`；
- 缺少配置、URL 无效或 SQLAlchemy 连接失败时返回安全状态，不返回连接字符串。

当前阶段不需要修改上述代码。进入数据库实现前仍需补充：

- 明确区分运行时连接与迁移连接；
- SQLAlchemy Session 和事务生命周期；
- 连接池参数与连接超时；
- `TEST_DATABASE_URL` 及测试数据库防误连保护；
- 对正式环境禁止 `DEBUG=true` 的校验。

这些属于阶段二的独立小任务，不能在连接身份未确认时提前实现。

## 3. Supabase 连接器结果

### 当前可见账户范围

连接器调用成功返回：

```text
organizations:
  - dreamqwq114-del's Org

projects: []
```

可以确认：

- Supabase 连接器已经连到某个 Supabase 账户；
- 该账户至少能看到一个组织；
- 该账户当前看不到任何项目；
- 没有可用于确认 `daily-fruit` 的 project ref、项目名称或项目 URL。

不能确认：

- 当前 Supabase 账户是否是用户打算使用的账户；
- `daily-fruit` 目标项目是否已经创建；
- 目标项目是否位于其他组织；
- 当前账户是否缺少目标项目成员权限；
- OAuth 连接是否没有获得目标项目的管理可见性；
- 远端数据库是否为空。

“项目列表为空”只说明当前连接范围内没有可见项目，**绝不等于数据库为空**。

## 4. 远端数据库只读审计结果

因为没有已确认的 project ref，以下项目均未执行，也没有结果：

| 审计项 | 状态 |
|---|---|
| 项目名称和 project ref | 未确认 |
| `public` schema 表 | 未读取 |
| 字段和数据类型 | 未读取 |
| 主键、外键、唯一约束 | 未读取 |
| 索引 | 未读取 |
| PostgreSQL 扩展 | 未读取 |
| Supabase 迁移记录 | 未读取 |
| Alembic 版本表 | 未读取 |
| RLS 是否启用 | 未读取 |
| Policies | 未读取 |
| Grants 与角色权限 | 未读取 |
| Security/Performance advisors | 未运行 |
| 测试数据或真实数据 | 未抽样 |
| 与八个计划表名的冲突 | 无法判断 |

没有调用 SQL 执行、迁移、seed、policy 或 grant 修改工具。

## 5. 最可能的阻塞原因

按当前证据从高到低排列：

1. Codex 中连接的是另一个 Supabase 账户；
2. `daily-fruit` 项目尚未创建；
3. 项目位于另一个组织，当前账户不是该组织或项目成员；
4. 用户虽然登录了 Supabase，但没有被授予具体项目权限；
5. Supabase OAuth 连接需要重新授权或刷新后才能看到新增的项目成员关系。

当前证据不足以在这些原因之间做唯一判断。

## 6. 用户需要完成的最少操作

1. 在 Supabase Dashboard 使用预期账户登录，确认目标项目确实属于 `daily-fruit`。
2. 只提供以下非秘密信息之一：
   - 目标 project ref；或
   - 目标项目名称和 Dashboard 项目 URL。
3. 确认当前 Codex 连接的 Supabase 账户已加入该项目所在组织，并拥有至少只读管理权限。
4. 如果 Dashboard 中能看到项目而 Codex 看不到：
   - 在 Codex 的 Supabase 连接中重新授权正确账户；
   - 完成浏览器 OAuth；
   - 重新加载会话；
   - 再次运行“列出项目”。

禁止提供数据库密码、secret key 或 service role key。

## 7. 项目可见后的只读审计顺序

只在用户确认 project ref 后执行：

1. 读取项目元数据并再次核对名称、ref 和组织；
2. 列出 `public` 表及详细字段和外键；
3. 读取约束、索引、RLS、policies 和 grants；
4. 列出扩展和迁移记录；
5. 检查 `alembic_version` 或其他迁移体系；
6. 只读统计候选表行数，并抽样判断是否为真实数据；
7. 检查八个计划表名冲突；
8. 运行 security 和 performance advisors；
9. 把结果追加到本文档；
10. 只有审计结论明确为兼容，才允许准备迁移。

## 8. 进入阶段二判定

当前判定：**不允许进入数据库实施阶段。**

解除阻塞必须同时满足：

- 目标 project ref 已由用户确认；
- 连接器能读取同一 project ref；
- `public` schema、迁移、RLS、policies、grants 和 advisors 已完成只读审计；
- 已确认不会覆盖未知表或数据；
- 用户批准阶段二的第一个写入任务。

## 9. 官方资料核对

本次核对了 2026-07-31 可访问的 Supabase changelog。与本项目相关的变化包括：

- 新表是否自动暴露给 Data API 的平台默认值正在变化，不能依赖隐含默认值；
- 扩展版本固定行为发生变化，后续必须读取实际扩展版本，不能只相信迁移文本。

阶段二安全设计以显式 grants、显式 RLS 和最小权限为准：

- [Securing your API](https://supabase.com/docs/guides/api/securing-your-api)
- [Connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [MCP setup](https://supabase.com/docs/guides/getting-started/mcp)

