# 阶段三：推荐算法设计

## 1. 范围

阶段三只实现可独立测试的纯 Python 推荐算法，不连接数据库、不创建
Repository、Router 或前端页面。后续 API 阶段负责把 ORM 数据转换为本阶段的输入对象，
并把结果持久化。

旧版 `stage-1-plan.md` 中的阶段编号已被实际实施过程取代：数据库结构、迁移、安全和
seed 已在仓库的 S2 完成，因此当前 S3 对应原计划中的“纯 Python 推荐算法”。

## 2. 输入和输出边界

算法使用与 ORM 分离的不可变输入对象：

- `RecommendationUser`：地区、甜酸软脆偏好、价格等级和便利性偏好；
- `RecommendationFruit`：水果属性、营养特征、季节窗口和启用状态；
- `FruitPreference`：单个水果的偏好分和禁止标记；
- `RecommendationContext`：月份、近期水果顺序、历史反馈和随机种子；
- `RecommendationResult`：两项有序推荐、各项得分明细和 2 到 4 条理由。

输入对象不持有 SQLAlchemy Session，也不触发延迟加载。Repository 在后续阶段一次性
预加载所需数据，避免算法产生 N+1 查询。

## 3. 候选过滤

依次排除：

1. `is_active=false`；
2. `is_forbidden=true`；
3. 显式偏好分为 `-1`，且启用“严格排除不喜欢”策略；
4. 存在适用于用户地区或“全国”的季节记录，但当前月份不在任何相关窗口内。

没有用户地区或“全国”季节记录视为数据缺失，保留候选并使用 `0.35` 的季节缺失分，
而不是误判为完全不适用。少于两个候选时抛出可理解的领域错误。

普通窗口使用 `start <= month <= end`；跨年窗口使用
`month >= start or month <= end`。

## 4. 子分数

全部分数在进入总分前限制到 `[0, 1]`：

- `season_score`：相关且当季的最高季节分；缺失时为 `0.35`；
- `preference_score`：甜、酸、软、脆四维相似度占 70%，单果显式偏好占 30%，
  再叠加有上限的历史反馈调整；
- `nutrition_diversity_score`：维生素 C、纤维、钾、叶酸和类胡萝卜素归一化值的平均值；
- `history_diversity_score`：近期未出现为 `1`，越近出现惩罚越强；
- `convenience_score`：水果便利度与用户期望的接近程度；
- `price_match_score`：同级为 `1`，相差一级为 `0.5`，相差两级为 `0`。

反馈只调整偏好子分数：`liked`、`eaten` 为正向；`disliked`、`expensive`、
`tired_of_it`、`unavailable`、`change_requested` 为不同程度负向。总调整限制在
`[-0.35, 0.25]`，最终仍限制到 `[0, 1]`。

## 5. 基础总分

权重只在 `recommendation_service.py` 的常量中定义：

```text
base_score =
    season_score * 0.35
  + preference_score * 0.25
  + nutrition_diversity_score * 0.20
  + history_diversity_score * 0.10
  + convenience_score * 0.05
  + price_match_score * 0.05
```

第一项默认取最高基础分。传入 `random_seed` 时，只在距最高分不超过 `0.02` 的候选中
使用有种子的选择；相同输入和种子必须得到相同结果。

## 6. 营养互补和第二项

六个营养维度为能量、维生素 C、纤维、钾、叶酸和类胡萝卜素。算法先在当前候选集内
逐维做 min-max 归一化；某一维全部相同则统一记为 `0.5`。

互补分由两部分组成：

- 第一项较低维度被第二项覆盖的程度，占 80%；
- 两项营养轮廓差异，占 20%。

```text
second_score = base_score * 0.70 + complement_score * 0.30
```

第二项必须与第一项不同。该设计让营养互补可以改变纯基础分的第二名，同时不让低基础分
候选仅凭极端单项值获胜。

## 7. 推荐理由

每项返回 2 到 4 条结构化理由，使用已有 `ReasonCode`、`ReasonComponent` 和
`RecommendationReason` 契约。理由按实际贡献排序，可包含：

- 当前处于适宜购买月份；
- 符合甜、酸、软或脆偏好；
- 符合价格范围；
- 最近一段时间没有推荐过；
- 食用便利性符合偏好；
- 营养特点较丰富；
- 历史反馈偏正向；
- 与另一项的营养特点互补。

理由不得包含诊断、治疗、替代药物或保证改善身体问题的表述。

## 8. 稳定性与失败方式

- 不修改传入集合；
- 不使用全局随机状态；
- 不访问网络、环境变量或数据库；
- 缺失营养数据使用中性轮廓，不除零；
- 月份非法、ID 重复或候选不足时抛出明确领域错误；
- 所有输出分数限制在 `[0, 1]`。

## 9. 实现审查结论

- `recommendation_service.py` 只处理纯计算，没有 Session、SQLAlchemy 查询、网络或
  环境变量访问；
- 输入类型位于 `recommendation_types.py`，与 ORM 和 HTTP Schema 的职责保持分离；
- 结构化理由复用已有 `RecommendationReason` 契约，后续可稳定序列化到 JSONB；
- 相同输入顺序无关；只有显式传入 `random_seed` 时才在近似最高分窗口内选择；
- 缺失营养使用中性轮廓，相同营养维度不会除零；损坏的月份、分数和 ID 会明确失败；
- 现有演示数据已离线贯通，但数据库加载和持久化必须留给后续 Repository/API 阶段。
## V2 implementation status

The V2 formula, fruit identity contract, familiarity semantics, seven-profile
comparison and current acceptance evidence are maintained in
`docs/recommendation-v2-comparison.md` and `docs/audits/`. The V2 implementation
is in `backend/app/services/recommendation_service.py`; this document's older
V1 formula is retained as the historical baseline.
