# 推荐算法 V1 现状审计

审计日期：2026-08-01

## 审计范围与目标身份

- 本地代码版本：`0bf4705`。
- 唯一目标 Supabase：`Daily Fruit`，project ref `frzbbpocyzlqxljsrsiw`。
- 远端只读复核：PostgreSQL 17.6，`public.alembic_version=0004`；24 条水果、24 条营养、48 条季节、11 个用户、57 条用户偏好、11 条推荐、22 条推荐项、4 条反馈。
- 本轮在审计和基线阶段不修改 Supabase。

## 1. 完整调用链

1. `/api/recommendations/today` 或 `/api/recommendations/refresh` 进入 `recommendation_application_service`。
2. 应用服务从 Repository 批量读取 active 水果（含 nutrition/seasons）、当前用户偏好、最近 7 天水果 ID 和最近 30 天反馈。
3. `recommendation_mapper.py` 将 ORM 对象一次性转换为 `RecommendationFruit`、`RecommendationUser`、`RecommendationContext`。
4. 纯函数 `recommend_fruits()` 调用 `select_recommendation_pair()`。
5. V1 先调用 `score_candidates()`：硬过滤后计算单水果分数并排序。
6. 先选基础分最高（或 0.02 近邻池中的确定性随机项）作为第一种水果，再用营养互补分贪心选择第二种水果。
7. `_build_reasons()` 根据评分贡献生成最多 4 条理由。
8. 应用服务将两个结果保存为 `recommendations` 和 `recommendation_items`，API 再映射为响应。

## 2. V1 真实公式

季节：地区只匹配 `{user.region, "全国"}`；有匹配且当月命中时取最高 `season_score`，无相关地区数据为 `0.35`，有数据但不在月份内为 `0`，随后直接过滤掉不在季节内的水果。

口味相似度：

```text
taste_similarity = 1 - (
  |sweet - user_sweet| + |sour - user_sour|
  + |soft - user_soft| + |crisp - user_crisp|
) / 4
```

显式偏好归一化：`x<=0` 时为 `(x+1)/2`；`x>0` 时为 `0.5+x*0.25`，所以 `-1/0/1/2` 对应 `0/0.5/0.75/1`。

```text
preference_score = clamp(
  taste_similarity * 0.70
  + explicit_preference * 0.30
  + feedback_adjustment,
  0, 1
)
```

营养先在过滤后的候选集内对 6 项做 Min-Max；缺少 nutrition 的水果固定为 `0.5`。`nutrition_diversity_score` 实际是 vitamin C、fiber、potassium、folate、carotenoids 五项平均值，不是两种水果之间的多样性。

```text
base_score = season*0.35 + preference*0.25
           + nutrition_diversity*0.20 + history*0.10
           + convenience*0.05 + price_match*0.05
```

便利性为 `1-|fruit_convenience-user_convenience|`；价格为 `max(0, 1-0.5*|fruit_price-user_price|)`，因此低于预算也会扣分。历史为列表位置分档：未出现 `1.0`，第 1/2/3/更早位置为 `0/0.2/0.4/0.6`。反馈为按类型相加后限制在 `[-0.35,0.25]`，V1 的 `change_requested` 也会进入这个长期按水果聚合的调整。

第二种水果：

```text
complement = coverage*0.80 + contrast*0.20
second_score = candidate_base*0.70 + complement*0.30
```

其中 coverage 使用第一种水果六项归一化营养缺口加权，contrast 是六项绝对差的平均值。第一种和第二种输出分数口径不同。

## 3. 数据转换和排序含义

- `data/fruits_seed.json` 的 24 条记录通过名称与 CSV 连接；测试 fixture 用种子文件顺序生成 1 到 24 的临时 ID，生产环境 ID 由数据库 Identity 生成。
- ORM `Fruit` 加载 `nutrition`、`seasons` 后由 mapper 转成纯算法对象；算法不持有 Session。
- `recent_fruit_ids` 按推荐日期倒序、refresh 倒序、rank 升序读取，去重后第一个表示最近出现的水果；它只保留水果 ID，不保留日期、次数或是否吃过。
- `feedback_by_fruit` 查询最近 30 天、最多 100 条反馈，按创建时间倒序按水果聚合为字符串元组；反馈没有日期或行为强度，算法只看到类型列表。
- 用户必须先有用户档案；没有水果偏好记录时当前 V1 将它解释为显式分 `0.5`，没有“未尝试”状态。
- 地区必须与季节 `region` 精确相等或命中“全国”，不会做城市、省份、大区层级解析。

## 4. 高分拆解（华东、7 月、无偏好冷启动）

固定基线中：

- 芒果：`base=0.7909`，season `0.86`，preference `0.612`，nutrition `0.689`，history `1.0`，convenience `0.98`，price `1.0`。
- 牛油果：在该上下文被季节硬过滤，不能进入最终组合；这说明“第二种集中在牛油果”的问题依赖月份/地区数据，不能只靠现有单次基线判断。
- 榴莲：`base=0.7387`，season `0.82`，preference `0.612`，nutrition `0.596`，history `1.0`，convenience `0.98`，price `1.0`，并因互补获得第二项加权。

## 5. 24 种水果数据完整性

本地 JSON、nutrition CSV、season CSV 名称集合一致；每种水果均有 1 条营养数据和至少 1 条季节数据，当前远端计数为 24/24/48；分数和月份通过 seed Pydantic/数据库 CHECK 校验。口味、便利性、价格等级、季节分、营养 0~1 值和部分份量是演示性人工标注，不是每 100 克的权威营养测量，也没有逐项可靠来源字段。

当前数据缺少稳定英文 code、别名、份量克数、直接食用/处理方式、main/exploration/supporting 角色、处理/携带/储存/气味/常见度/尝鲜等级和数据质量字段；这正是 V2 数据模型升级的范围。

## 6. 当前测试覆盖缺口

已有测试覆盖跨年季节、硬过滤、V1 权重、营养互补、确定性随机、API 基础流程和 seed 幂等。但缺少：稳定全库营养基准、缺失营养置信度、份量换算、城市到全国层级、可供应但非当季不硬过滤、熟悉度/尝鲜约束、按日期衰减的历史和反馈、完整组合枚举、组合历史排除、支撑型水果、V2 理由边际贡献以及七个固定用户的分布回归。

