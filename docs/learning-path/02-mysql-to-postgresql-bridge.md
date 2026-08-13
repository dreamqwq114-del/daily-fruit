# MySQL 到 PostgreSQL、SQLAlchemy 与 Alembic 桥

## 可以直接迁移的知识

`SELECT`、列别名、`WHERE`、`NULL`、稳定排序、聚合、`GROUP BY/HAVING`、INNER/LEFT
JOIN、CASE、子查询、非递归 CTE、EXISTS、CAST、事务和“修改前先 SELECT”都能迁移。
业务目标、重复行、NULL 和连接基数的推理比背方言关键字更重要。

## 必须主动区分的方言

| MySQL/MariaDB 学习材料 | PostgreSQL / Daily Fruit |
| --- | --- |
| `USE database_name` | 连接时选择数据库；业务对象位于 `public` schema |
| `AUTO_INCREMENT` | `GENERATED ... AS IDENTITY` / SQLAlchemy `Identity` |
| `TINYINT(1)` 常作布尔 | 原生 `BOOLEAN` |
| `DATETIME` | 常用 `TIMESTAMP WITH TIME ZONE` |
| `JSON` | 项目历史快照使用 `JSONB` |
| `ON DUPLICATE KEY UPDATE` | PostgreSQL `ON CONFLICT ... DO UPDATE` |
| 反引号引用标识符 | 双引号引用；项目通常使用无需引用的小写名称 |
| `DESCRIBE table` | `information_schema`、DBeaver 元数据或 psql `\d` |
| `START TRANSACTION` | `BEGIN`/`START TRANSACTION` 均可；应用主要由 SQLAlchemy Session 管理 |
| `LIMIT` | PostgreSQL 也支持，但 ORM 常通过 `.limit()` 生成 |
| `COALESCE`、CTE、CASE | 两边都有，仍需核对具体类型与 NULL 行为 |

## PostgreSQL 项目特有入口

- partial unique index：只约束同日 `status='active'` 的推荐；
- UUID：外部认证身份，不用客户端提交的 user ID 授权；
- CHECK/FK/UNIQUE：数据库最终一致性边界；
- JSONB：冻结历史展示，不等于把所有字段都塞进 JSON；
- advisory lock：同用户推荐并发控制；
- RLS 与 grants：启用 RLS 不等于策略和权限正确；
- Alembic：用 revision 链管理结构，不在 Dashboard 手工改完就结束；
- SQLAlchemy：Repository 组合查询，Application Service 控制事务。

## 四个桥接实验

这些实验默认只读，禁止连接远程 Supabase。

### S1：方言翻译表

- TODO：从 MySQL 第 1、4、6、8 章各选一条只读查询；
- TODO：标出可原样迁移、需要替换、需要重新验证的部分；
- TODO：说明 `USE` 为什么不能原样复制到 PostgreSQL；
- 验收：翻译后仍保持列数、NULL、重复与排序合同。

### S2：读 `0014`，不执行

- TODO：写出两个 precheck 查询分别寻找什么坏数据；
- TODO：写出两个 CHECK 的业务语义；
- TODO：解释为什么 migration 不自动把坏数据改成某个默认值；
- 验收：能区分“拒绝迁移”“清洗历史数据”“改 DDL”三个动作。

### S3：从 SQL 到 ORM

- TODO：在 `recommendation_repository.py` 选一个查询，写出概念上的 SQL 操作顺序；
- TODO：标出 JOIN/eager load、filter、order、limit；
- TODO：说明 Repository 为什么不 commit；
- 验收：能从 ORM 代码说出它要读哪些表，而不是逐字符猜生成 SQL。

### S4：安全事务演练设计

- TODO：为可丢弃本地库写“确认数据库 → SELECT 预览 → BEGIN → 修改 → 验证 → ROLLBACK”
  的步骤清单，只写占位任务，不填实际连接串；
- TODO：列出禁止目标：远程 Supabase、未知数据库、业务用户数据；
- 验收：能解释为什么测试 skip 不等于数据库行为通过。

## 边界提醒

桌面 MySQL 课程的目标方言是 MySQL 8.0，历史实跑环境是 MariaDB 10.4.32；本次连接
检查发现服务未启动。恢复环境后应先运行 `00_setup/verify_database.sql`，不能直接引用
旧审计声称当前可运行。旧 T-SQL 课程中的 `TOP`、`DB_NAME()` 和方括号标识符不应混入
MySQL 或 PostgreSQL 主线。

状态可能变化，开始 SQL 学习前重新运行只读检查：

```powershell
& 'D:\xampp\mysql\bin\mysql.exe' --version
Test-NetConnection 127.0.0.1 -Port 3306
& 'D:\xampp\mysql\bin\mysql.exe' -uroot -e "SELECT VERSION();"
```

前两条只检查客户端与端口；第三条只有在本地服务已启动且该本机练习账号仍适用时才
执行。连接失败就先恢复本地练习环境，不改业务数据库，也不把历史运行记录当作当前结果。
