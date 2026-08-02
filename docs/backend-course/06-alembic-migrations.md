# Alembic Migration

## 学习目标

理解 ORM 变化与数据库变化的区别，能读取 `revision/down_revision` 链，知道
`upgrade`、`downgrade` 的责任和为什么不能用手工 SQL 代替 migration 记录。

## ORM 不是数据库历史

SQLAlchemy model 描述“现在希望如何映射”；Alembic migration 描述“数据库如何从
旧版本演进到新版本”。删除 ORM 字段不会自动删除远程列，修改 migration 文件也不
会回放已经执行的历史。因此 schema 变更要同时审查 model、migration、schema、seed
和测试。

## 当前 revision 链

```mermaid
flowchart LR
    m1[0001 基础业务表] --> m2[0002 RLS 与权限]
    m2 --> m3[0003 Auth 绑定]
    m3 --> m4[0004 migration 表权限]
    m4 --> m5[0005 推荐 V2 字段]
    m5 --> m6[0006 消费周期]
    m6 --> m7[0007 购买条件]
```

这里的编号是仓库当前事实，不应写成未来永久规则。检查 head 时应读取
`backend/alembic/versions/` 中全部文件或运行安全的 `alembic history`；不能只看
最新文件的 `down_revision`。

## 三个演进案例

1. `0001_create_daily_fruit_tables.py` 创建八张 public 业务表、主键、外键、检查、
   索引和 recommendation active partial unique index。
2. `0005_recommendation_v2_data_model.py` 增加水果身份/供应/熟悉度、用户
   `discovery_level`、偏好熟悉度和推荐 item 的拆分分数；downgrade 先检查数据是否
   会丢失，再移除列。
3. `0007_user_market_access.py` 只增加 `market_access_level` 与
   `accepts_online_purchase`，并明确注释“当前只进入资料保存链路”。

`0002` 和 `0004` 主要是安全/权限操作，不应被误画成普通字段 migration。

## upgrade 与 downgrade

`upgrade` 应在目标环境确认后按链执行，`downgrade` 应只删除该 revision 拥有的对象。
生产 downgrade 具有破坏性，通常只在可丢弃测试数据库演练。当前迁移中的某些安全
回滚刻意不重新开放浏览器权限，这是安全取舍，不是“每一步都完全反向”。

## 检查流程

```text
读取所有 revision/down_revision
→ 推导最终表、列、约束、索引
→ 对照 ORM metadata 和静态测试
→ 在隔离数据库执行 upgrade/downgrade（若获授权）
```

本教材只做源码和静态事实导读，不执行远程 migration。仓库的集成 migration 测试在
配置安全本地测试库时才运行；没有安全测试库时应如实跳过。

## 常见错误修改

- 直接在 Supabase Dashboard 加列却不生成 Alembic revision；
- 修改已经发布的旧 migration 期待远程自动同步；
- downgrade 误删其他 revision 创建的约束；
- 把 auth/storage 系统 schema 当作本项目业务表迁移。

## 小练习

用文本读取 `0005`、`0006`、`0007` 的 `down_revision`，画出它们和 `users`/`fruits`
的变化。指出哪个字段在 migration 中明确标注为“只保存”。不要执行 `upgrade`。

## 本章事实来源

| 教学结论 | 源文件 | 符号/文件 | 事实类型 |
| --- | --- | --- | --- |
| revision 链 | `backend/alembic/versions/0001...0007` | `revision`、`down_revision` | migration 事实 |
| 基础 schema | `0001_create_daily_fruit_tables.py` | `upgrade` | migration 事实 |
| RLS 与权限 | `0002_secure_daily_fruit_tables.py` | `upgrade/downgrade` | migration 事实 |
| 可丢失数据保护 | `0005_recommendation_v2_data_model.py` | `downgrade` | migration 事实 |
| 静态一致性测试 | `backend/tests/test_migration_static.py` | test functions | 测试事实 |

## 本章总结

Migration 是数据库演进的可审计历史。任何结构变化都必须同时思考现有数据、回滚
风险、ORM 合同和测试隔离。`n