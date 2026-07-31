# daily-fruit 项目长期规则

本文件适用于整个 `daily-fruit` 仓库。

## 1. 范围

- 只修改当前明确任务允许的文件；
- 不读取、复用或修改 `daily-fruit` 以外的 Supabase 项目；
- 每次只执行一个可验收的小任务；
- 不为了匹配示例目录进行无意义移动或重构；
- 开始前读取相关代码、设计文档和当前 Git 状态。

## 2. 分层

- Vue 只通过 HTTP 调用 FastAPI，不直接操作水果、用户偏好、推荐历史等业务表；
- Router 只处理 HTTP 输入、响应和依赖注入；
- Service 处理业务逻辑、推荐算法、授权检查和事务编排；
- Repository 处理数据库查询和持久化；
- SQLAlchemy Model 与 Pydantic Schema 必须分离；
- 推荐算法不得写在 Router 或 Vue 中；
- API 请求统一放在 `frontend/src/api/`。

## 3. 数据库与迁移

- Alembic 是业务数据库结构的主要版本管理工具；
- 不在 Supabase Dashboard 手工改表后遗漏迁移；
- 不修改 Supabase `auth`、`storage` 等系统 schema；
- 未确认目标 project ref 前禁止数据库写操作；
- 每次数据库操作前显示并核对 project ref；
- 未完成现有结构、迁移、RLS、policies、grants 和数据审计前禁止建表；
- 不使用 `IF NOT EXISTS` 掩盖未知同名对象；
- 不删除未知表、字段、策略、数据或迁移记录；
- 生产数据优先通过向前迁移修复，不直接 destructive downgrade；
- 任何 DROP、TRUNCATE、不可逆 ALTER 或批量删除必须停止并向用户汇报；
- 数据库写入失败后读取完整错误，进行最小修复，不通过删功能绕过。

## 4. Supabase 安全

- 禁止提交 `.env`、数据库密码、secret key 或 service role key；
- 前端禁止持有数据库连接字符串或高权限密钥；
- `backend/.env` 必须被 Git 忽略；
- 业务表位于暴露 schema 时必须显式审查 grants 和 RLS；
- 不能把“连接器返回 0 个项目”解释为数据库为空；
- 身份、组织、project ref 或权限不确定时立即停止；
- 不猜测目标项目，不连接名称相似的项目；
- service role key 不是 PostgreSQL `DATABASE_URL`；
- 日志、README、测试输出不得包含完整连接字符串。

## 5. 测试隔离

- 单元测试默认不得访问网络或正式数据库；
- 数据库集成测试使用可丢弃 PostgreSQL，不使用 SQLite 替代 PostgreSQL 特性；
- 测试代码默认拒绝 Supabase 正式 host；
- Alembic downgrade 只在可丢弃测试库验证；
- seed 先 dry-run，再在测试库连续运行两次验证幂等；
- 不在测试 fixture 中 truncate 或 drop 正式数据库对象。

## 6. 修改与验收

修改前：

1. 检查 Git 状态；
2. 阅读允许修改的文件；
3. 简述本任务将修改什么；
4. 确认停止条件。

修改后：

1. 列出修改文件；
2. 运行与改动相称的测试；
3. 前端变化运行 `npm run build`；
4. 后端变化运行 `pytest`；
5. 数据库变化运行 Alembic 和 Supabase 实际结构复核；
6. 扫描秘密；
7. 报告测试结果、风险和未完成事项。

不得把静态审查描述为运行时验证，也不得把本地测试描述为 Supabase 验证。

## 7. 当前门禁

截至 `docs/stage-1.5-supabase-audit.md` 的当前记录：

- Supabase 连接器可见项目数为 0；
- `daily-fruit` 目标 project ref 未确认；
- 禁止 ORM、Alembic、DDL、迁移、seed 和远端写入；
- Luna 的下一任务只能是 `S2-00` 只读连接门禁。

