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
- Vue 可以使用 Supabase 客户端完成 Auth，但只能使用项目 URL 和公开的
  publishable key，不得用它直接访问业务表；
- FastAPI 必须验证 Supabase access token，并从已验证的 `sub` 推导当前用户；
- 业务 API 不得信任客户端提交的 `user_id` 作为授权依据；
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

- 已确认唯一目标项目为 `Daily Fruit`，project ref 为
  `frzbbpocyzlqxljsrsiw`；
- 已完成 `public` schema、迁移、扩展、RLS、policies、grants、数据和
  advisors 的只读审计；
- S2-08 写入前确认目标项目没有业务表或业务数据，八个计划表名没有
  冲突；
- `S2-00` 已由提交 `3d71816` 完成；
- `S2-01` 已由提交 `742eeeb` 完成，runtime、migration 和 test URL
  已隔离，测试 URL 默认拒绝 Supabase 正式域名；
- `S2-02` 已由提交 `ae83235` 完成，八张业务表的 SQLAlchemy
  metadata、约束、索引和删除策略已通过静态测试；
- `S2-03` 已由提交 `fab7a89` 完成，Pydantic Schema 和验证测试已与
  ORM 分离；
- `S2-04` 已由提交 `f2e4a21` 完成，Alembic 只接受显式的 test 或
  migration 连接用途，受控文件中不保存数据库 URL；
- `S2-05` 已由提交 `ddbc214` 完成，基础迁移只包含八张业务表及批准的
  约束和索引，未包含远端操作或系统 schema 变化；
- `S2-06` 已由提交 `36c3e29` 完成，基础迁移已在 `daily_fruit_test`
  实测 upgrade、downgrade、结构一致性、约束和删除策略；
- `S2-07` 已由提交 `a3a417d` 完成，安全迁移已在本地实测八表 RLS、
  deny-by-default、表/序列 revoke 和已知函数权限修复；
- S2-08 写入前只读复核再次确认唯一目标为 `Daily Fruit`
  (`frzbbpocyzlqxljsrsiw`)，`public` 用户表、迁移和业务数据仍为空；
- `S2-08` 已完成，远端 `public.alembic_version=0002`，八张业务表、
  RLS、grants、约束、索引、迁移记录和 advisors 已复核；
- `S2-09` 已由提交 `cb935b6` 完成，24 种水果及营养、季节演示文件
  已通过静态范围、自然键和口径校验；
- `S2-10` 已由提交 `1174603` 完成，seed 的 dry-run、事务回滚、
  UTF-8 SQL 输出和两次本地幂等执行已通过测试；
- S2-11 写入前再次确认唯一目标 project ref、远端 schema 版本为
  `0002`，且 fruits、nutrition、seasons 和行为表计数均为 0；
- `S2-11` 已完成：远端 seed 连续执行两次后计数稳定为 24/24/48，
  重复、孤立和非法范围记录均为 0，行为表均为空；
- `public.rls_auto_enable()` 的两项 security advisor WARN 已修复，
  event trigger 仍启用；当前 advisor 只剩已解释的 INFO；
- S3 推荐算法已完成并通过专项及全量回归；本阶段没有连接或修改 Supabase，也没有
  新增迁移、seed、Repository、Router、正式 API 或 Vue 页面。
- S4 后端 API 已完成并通过本地 PostgreSQL 全量测试；本阶段没有修改远端 Supabase，
  也没有新增 schema migration。
- 后续 API 接入必须把 ORM 数据一次性转换为 `RecommendationUser`、
  `RecommendationFruit` 和 `RecommendationContext`，不得让纯算法持有 Session 或
  产生 N+1 查询。
- S5 前端已完成；S6 已获授权接入 Supabase Auth、受保护 FastAPI 和公网业务链路。
- 前端对业务数据只能调用 FastAPI；Supabase 客户端仅限 Auth，不得包含数据库 URL、
  secret key 或 service role key。
- S6 生产迁移只允许新增已审查的 `users.auth_user_id` 绑定，不得修改 seed 或其他表。
- S6 已部署：远端迁移为 `0004`；V2 阶段后续迁移为 `0005`，FastAPI Cloud 业务 API 强制 JWT，GitHub Pages 已连接；
  后续不得退回 localStorage user ID 或公开无认证写接口。
- 不得启用 Supabase 匿名登录；后端必须拒绝 `is_anonymous=true` 的 token。
- 阶段七明确关闭注册邮箱确认；注册必须立即返回 session，不得恢复注册确认邮件，除非先完成新的安全设计审查。
- 关闭注册确认不等于关闭密码找回邮件；`/auth/callback` 保留给未来的找回流程。
- GitHub Pages 发布必须在构建时验证公开 API URL、Supabase URL 和 publishable key，
  任何一项缺失都不得生成可部署产物。
- 如后续任务发现必须改变 schema，立即停止并先更新设计与授权门禁。
## V2 recommendation rules

- `RecommendationUser`, `RecommendationFruit` and `RecommendationContext` are
  the pure-algorithm boundary; the algorithm must not hold a database session.
- V2 fruit identity, familiarity, availability and score fields are owned by
  SQLAlchemy/Alembic and must stay synchronized with the actual Daily Fruit
  Supabase project before seed or migration work.
- `has_tried=NULL` means unknown; do not silently convert it to tried or
  forbidden. A favorite and an explicit not-tried answer are an invalid
  combination at the API boundary.
- Run backend tests, frontend tests/build, migration SQL checks and a secret
  scan after changes. Do not claim seed idempotence without running it twice.
