# 引导练习答案

答案用于核对思路，不代表学习者已经实现这些功能。每题先给项目事实，再补充通用
解释；如果题目要求运行，仍应在本地安全环境自行复核。

## 基础答案

### B1

`RecommendationFruit` 提供水果身份、口感、价格、便利性、营养和季节等输入；
`ScoredFruit` 在此基础上携带 `ScoreBreakdown` 和 `base_score`。这是领域对象
之间的转换，不是 ORM 保存。

### B2

`User` 是 SQLAlchemy ORM，带 `fruit_preferences` 和 `recommendations` relationship；
`UserRead` 是 Pydantic API 输出；`RecommendationUser` 是 mapper 生成的纯 dataclass，
只保留算法读取的字段。相似名字不代表可以互换。

### B3

下面是只读教学示例，表名和连接关系来自 `0001`，但请不要对生产库执行：

```sql
-- 只读示例；可在隔离本地 schema 上验证；不包含真实用户数据
SELECT r.id, r.recommendation_date, f.name, ri.rank
FROM public.recommendations AS r
JOIN public.recommendation_items AS ri ON ri.recommendation_id = r.id
JOIN public.fruits AS f ON f.id = ri.fruit_id
WHERE r.user_id = 1
ORDER BY r.recommendation_date DESC, ri.rank;
```

这是可直接对应当前最终 schema 的简化只读查询；`user_id=1` 只是虚构示例。

### B4

Repository 的 `add_recommendation` 先 add/flush，让 identity ID 可用；
`_persist_recommendation` 还需要把两条 item 和主记录放进同一事务图。外层 service
最后 commit，算法失败或数据库异常时才能整体 rollback。

### B5

Facade 的 `recommend_fruits` 调用 `select_recommendation_pair`，后者使用
`fruit_evaluation` 的候选评分和 `pair_selection` 的组合逻辑；返回后 Facade 调用
`reasons._build_reasons`，再组装两个 item 和一个 result。

## 中级答案

### M1

已有 active 时：Router → auth/current user → `get_today_recommendation` → lock →
`get_active_recommendation` → API mapper，算法不运行。没有 active 时还会查询水果、
偏好、历史、feedback，Mapper 生成领域输入，Facade 返回结果，再 flush/commit，
提交后重新加载详情。

### M2

inactive、forbidden、明确不可用和某些尝鲜规则是硬过滤；季节和价格是评分输入，
通常属于软因素。`excluded_pair` 是组合硬约束；历史新颖度通常是分数或短期冷却，
要结合调用阶段判断，不能把所有“历史”都当作同一种规则。

### M3

`None` 表示未知，不能当作没吃过；`False` 是明确没吃过；`True` 是明确吃过。
保守 level 0 会排除明确未尝试水果；level 1/2 的组合规则允许更宽松，但仍受当前
`_pair_is_legal` 约束。实际语义来自 `filter_eligible_fruits` 和 `_pair_is_legal`。

### M4

先按 `BASE_SCORE_WEIGHTS` 对六个子分数做加权求和，再加 `feedback_adjustment`，
最后用 `clamp_score` 限制到 0～1。权重和为 1 只是当前代码的校验，不代表分数是
概率或准确率。

### M5

第一阶段同时保留完整组合冷却并尽量避开昨日水果；第二阶段放开昨日水果但保留组合
冷却；第三阶段放开完整组合冷却。`excluded_pair` 在 `_pair_is_legal` 最先检查，永远
不能恢复。

### M6

mapper 将 ORM Decimal 转成算法 float，将缺失营养保留为 `None`，将供应缺失标为
`unknown`，并明确不把购买条件字段塞入 `RecommendationUser`。这些处理决定了算法
看到的输入，因而 mapper 是语义边界，不是普通字段复制。

## 高级答案

### A1

测试应让 `recommend_fruits` 抛出 `RecommendationError`，调用 refresh 后断言异常被
转换为冲突；随后查询同一日期的推荐，旧记录 status 仍为 `active`，且没有持久化新
active。原因是 status 改动虽在 flush 后发生，但 commit 尚未执行，Session 依赖会 rollback。

### A2

清单至少包括：新增 revision 与正确 `down_revision`；ORM 字段；Pydantic 输入/输出；
mapper 语义；默认值和 CHECK；Repository 查询；算法是否读取；两次 seed 幂等；upgrade/
downgrade 在隔离库验证；旧数据和回滚丢失风险。不要只新增一列就宣称完成。

### A3

如果去掉水果查询的 `selectinload`，循环访问 `fruit.nutrition`、`fruit.seasons` 可能
触发额外 SELECT，形成 N+1。验证可使用 SQLAlchemy engine 日志或查询计数 fixture，
而不是改变推荐结果。当前 Repository 已通过 selectinload 表达意图。

### A4

重复率可按用户/日期窗口计算“与前几日重复的水果或组合”占比；覆盖率可按推荐过的
不同 fruit ID 除以 active fruit 数；反馈接受率应明确是 liked/eaten 事件除以可评价 item，
并按时间窗口和用户分组。它们是可改进方向，不是当前代码已实现的线上指标。

### A5

`unavailable` 可能反映供应，不是口味；`expensive` 反映价格环境，不一定是不喜欢；
`change_requested` 只说明用户想换组，也可能是重复、时间或购买原因。因此当前代码把
它们作为带时间的 feedback 事件或特定调整，而不是永久 `preference_score=-1`。

### A6

先保存 ORM、完整 migration 链、测试失败和数据库可见性证据；标记“仓库不一致”，
停止生成确定 ER 结论。不能选择“看起来较新”的一方，也不能为教材方便修改生产代码。

## 本章事实来源

答案主要依据 `backend/app/services/`、`backend/app/models/`、
`backend/alembic/versions/` 和 `backend/tests/`；通用事务和测试解释是通用知识，
没有把它们伪装成当前项目独有规则。`n