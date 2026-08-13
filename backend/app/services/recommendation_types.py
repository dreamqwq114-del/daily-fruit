"""推荐核心使用的纯 Python 数据合同。

这些 frozen/slots dataclass 是 ORM 与算法之间的边界：它们不携带 Session，
便于用固定输入测试季节、过滤、评分、组合和理由生成。字段的 ``None``、
``False`` 和数值并不是简单的默认值，而是跨 Repository、mapper 与纯算法
传递的业务语义。新增字段前应先确认 mapper、算法和测试是否都需要它。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Sequence

from app.schemas.recommendation import RecommendationReason


@dataclass(frozen=True, slots=True)
class NutritionProfile:
    """水果营养特征；``None`` 表示缺失而不是零。

    同一类型既承载 mapper 传入的原始演示值，也承载归一化后的 0～1 值；
    具体处于哪个阶段由调用方决定。缺失特征会降低 pair complement 的
    数据覆盖置信度，不能被悄悄填成中性值或 0。
    """

    energy: float | None = None
    vitamin_c: float | None = None
    fiber: float | None = None
    potassium: float | None = None
    folate: float | None = None
    carotenoids: float | None = None


@dataclass(frozen=True, slots=True)
class SeasonWindow:
    """一条地区和月份季节/供应窗口，支持跨年月份。

    ``region_level`` 只提供算法当前使用的匹配层级；``season_score`` 描述
    月份适宜度，``availability_score`` 描述供应可得性，``supply_status``
    则可以把 ``unavailable`` 作为硬过滤。缺失记录不是一条窗口，而是在
    ``evaluate_season`` 中使用单独的 fallback。
    """

    region: str
    start_month: int
    end_month: int
    season_score: float
    region_level: str = "national"
    availability_score: float = 0.45
    supply_status: str = "unknown"
    data_scope: str = "harvest"
    data_quality: str = "unverified"
    cultivation_type: str = "unknown"
    source_note: str | None = None
    source_year: int | None = None
    is_scoring_enabled: bool = False


@dataclass(frozen=True, slots=True)
class FruitPreference:
    """用户对单个水果的显式态度、禁止和熟悉度信号。

    ``is_forbidden=True`` 是最高优先级的安全硬约束。``has_tried`` 的三态
    语义是：``True`` 明确吃过，``False`` 明确没吃过，``None`` 或无记录
    表示 UNKNOWN；UNKNOWN 不等于普通偏好，也不等于没吃过。设计上
    ``willing_to_try`` 只应描述 ``has_tried=False`` 的探索意愿，
    ``preference_score`` 只应描述已经吃过的显式态度；当前过滤/评分代码
    仍会在部分 UNKNOWN 兼容路径读取这些值，详见对应 service 注释和最终
    审计报告。前端约定的偏好档位通常为
    -1/0/1/2（不喜欢、无所谓、喜欢、非常喜欢），但这里的数据类本身不
    负责校验取值或强制这两个字段的关联。
    """

    preference_score: float | None = None
    is_forbidden: bool = False
    has_tried: bool | None = None
    willing_to_try: bool | None = None


@dataclass(frozen=True, slots=True)
class SelectionOption:
    """一个父水果下可购买、可辨认的消费类型档案。

    选项不是新的顶层水果，也不携带营养、价格或季节数据。可空口感字段
    在进入推荐核心前由 resolver 继承父水果值，避免构造不存在的平均档案。
    """

    id: int
    fruit_id: int
    code: str
    name: str
    sweet_score: float | None = None
    sour_score: float | None = None
    soft_score: float | None = None
    crisp_score: float | None = None
    is_default: bool = False
    is_active: bool = True
    display_order: int = 1
    data_quality: str = "low"
    data_source_note: str | None = None
    texture_score: float | None = None
    ripe_storage_score: float | None = None
    convenience_score: float | None = None


@dataclass(frozen=True, slots=True)
class SelectionOptionPreference:
    """用户对一个消费类型的明确态度；缺失记录表示 unknown。"""

    user_id: int
    fruit_id: int
    option_id: int
    preference: str


@dataclass(frozen=True, slots=True)
class HistoryEvent:
    """历史展示/食用聚合事件，用于时间衰减去重。

    ``occurred_on`` 是推荐发生的业务日期，不是本次运行时间；只有保留它
    才能计算距今天的衰减。``times_shown`` 与 ``eaten_count`` 分别表达
    曝光负担和实际吃过的重复负担，数据库查询窗口与算法内部的衰减常数
    是两个不同概念。
    """

    fruit_id: int
    occurred_on: date
    times_shown: int = 1
    eaten_count: int = 0


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    """带时间的用户反馈，用于反馈调整衰减。

    ``feedback_type`` 是一次事件（例如 ``liked`` 或 ``unavailable``），
    ``occurred_at`` 决定它对当前分数的影响应衰减多久。刷新产生的
    ``change_requested`` 会被保留为会话事件，但当前评分逻辑不把它当作
    长期正负偏好。
    """

    fruit_id: int
    feedback_type: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationFruit:
    """算法需要的水果快照，脱离 SQLAlchemy ORM 后仍可独立评分。

    口感、便利性、价格和用户偏好进入单水果评分；``novelty_level`` 与
    展示分组只作为元数据，不直接改变分数。营养和 seasons 由后续阶段分别
    用于归一化、地区月份判断和组合评分。``is_active`` 与
    ``daily_recommendation_role`` 在候选过滤阶段决定是否允许进入评分，
    因而不能被当作仅供展示的元数据。字段默认值主要服务旧数据兼容，
    mapper 必须谨慎选择中性/保守 fallback，避免缺失数据制造虚假的优势。
    """

    id: int
    name: str
    sweet_score: float
    sour_score: float
    soft_score: float
    crisp_score: float
    convenience_score: float
    average_price_level: int
    category: str = ""
    # Presentation-only grouping retained for API compatibility; the core
    # recommendation score must never read it.
    display_group: str = ""
    taste: str = ""
    code: str = ""
    aliases: tuple[str, ...] = ()
    default_portion_grams: float = 100.0
    direct_eating: bool = True
    consumption_mode: str = "direct"
    daily_recommendation_role: str = "main"
    preparation_difficulty: float = 0.5
    portability_score: float = 0.5
    messiness_score: float = 0.5
    storage_difficulty: float = 0.5
    aroma_intensity: float = 0.5
    commonness_score: float = 0.5
    novelty_level: int = 1
    data_quality: str = "low"
    data_source_note: str | None = None
    is_active: bool = True
    nutrition: NutritionProfile | None = None
    seasons: tuple[SeasonWindow, ...] = ()
    selection_options: tuple[SelectionOption, ...] = ()
    texture_score: float | None = None
    ripe_storage_score: float | None = None
    typical_purchase_stage: str | None = None
    ripening_note: str | None = None


@dataclass(frozen=True, slots=True)
class RecommendationUser:
    """算法需要的用户画像；不包含 auth UUID 或数据库主键。

    ``discovery_level`` 是整体尝鲜倾向，不能代替单个水果的
    ``has_tried``。当前对象刻意不包含 ``market_access_level``、
    ``accepts_online_purchase`` 和消费周期字段，所以这些资料即使保存到
    数据库，也不会在本版本的推荐排序中生效；要接入必须同时修改 mapper、
    算法合同和测试。
    """

    region: str
    sweet_preference: float | None
    sour_preference: float | None
    soft_preference: float | None
    crisp_preference: float | None
    price_level: int
    convenience_preference: float
    city: str = ""
    discovery_level: int = 1
    fruit_preferences: Mapping[int, FruitPreference] = field(
        default_factory=dict
    )
    option_preferences: Mapping[int, tuple[SelectionOptionPreference, ...]] = field(
        default_factory=dict
    )
    texture_preference: float | None = None


@dataclass(frozen=True, slots=True)
class RecommendationContext:
    """一次推荐计算的日期、历史、反馈、刷新排除和随机种子。

    ``today`` 是历史/反馈衰减的时间锚点；``feedback_events`` 优先于旧的
    ``feedback_by_fruit`` 聚合输入，后者仅为兼容旧调用者。``excluded_pair``
    用于换一组时排除上一组，``cooldown_pairs`` 用于最近几天的组合硬冷却，
    ``previous_pairs`` 只用于更长期的组合新颖度；``random_seed`` 只允许在
    近优组合集合中做可复现选择。三者不能混用，否则 30 天历史会被误当成
    30 天硬过滤，候选池容易过快枯竭。
    """

    month: int
    today: date | None = None
    recent_fruit_ids: tuple[int, ...] = ()
    feedback_by_fruit: Mapping[int, Sequence[str]] = field(
        default_factory=dict
    )
    random_seed: int | None = None
    exclude_disliked: bool = True
    history_events: tuple[HistoryEvent, ...] = ()
    feedback_events: tuple[FeedbackEvent, ...] = ()
    # 最近短窗口内出现过的完整组合；正常阶段硬性禁止，候选不足时可放宽。
    cooldown_pairs: tuple[frozenset[int], ...] = ()
    # 更长历史窗口内出现过的组合，只作为新颖度软分，不是硬排除。
    previous_pairs: tuple[frozenset[int], ...] = ()
    excluded_pair: frozenset[int] | None = None
    allow_supporting: bool = False


@dataclass(frozen=True, slots=True)
class SeasonEvaluation:
    """季节匹配结果，包含可用性与供应状态。

    ``has_relevant_data=False`` 表示没有任何适用地区层级记录；这与有记录
    但当前月份不命中的 ``is_in_season=False`` 不同。``region_rank`` 保存
    当前选择所依据的地区层级，便于理由和后续审计解释为什么采用该窗口。
    """

    score: float
    has_relevant_data: bool
    is_in_season: bool
    availability_score: float = 0.45
    supply_status: str = "unknown"
    region_rank: int = 0
    has_harvest_data: bool = False
    has_market_data: bool = False
    harvest_data_quality: str = "unverified"
    market_data_quality: str = "unverified"
    market_region_matched: bool = False
    used_market_fallback: bool = False
    season_reason_eligible: bool = False
    market_reason_eligible: bool = False


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """单水果评分的可解释子分数，供公式和理由生成共同使用。

    ``explicit_preference``、``taste_match``、季节供应、价格、便利和历史
    进入当前基础公式；``feedback_adjustment`` 在加权基础分之后有界叠加。
    ``nutrition_diversity_score``、``familiarity_score`` 和
    ``preference_score`` 是算法/返回合同中的细分指标，但不是都直接作为
    独立权重项。不要因为字段存在就假设它已经改变排序。
    """

    explicit_preference: float
    taste_match: float
    availability_and_season: float
    price_match_score: float
    convenience_score: float
    history_diversity_score: float
    feedback_adjustment: float = 0.0
    season_score: float = 0.0
    availability_score: float = 0.45
    nutrition_diversity_score: float = 0.0
    familiarity_score: float = 0.5
    known_nutrition_ratio: float = 0.0
    preference_score: float = 0.0
    configured_dimension_count: int = 0
    configured_weight_sum: float = 0.0
    configured_dimensions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScoredFruit:
    """水果及其单项分数和季节评估。

    ``base_score`` 是单水果个人匹配分（含反馈调整），不是最终 pair 分；
    组合阶段还会加入第二个水果、营养互补、感官差异和组合新颖度。
    """

    fruit: RecommendationFruit
    base_score: float
    scores: ScoreBreakdown
    season: SeasonEvaluation
    resolved_candidate: "ResolvedFruitCandidate | None" = None


@dataclass(frozen=True, slots=True)
class ResolvedFruitCandidate:
    """进入完整评分前确定的唯一父水果消费类型快照。"""

    fruit: RecommendationFruit
    effective_sweet_score: float
    effective_sour_score: float
    effective_soft_score: float | None
    effective_crisp_score: float | None
    resolved_option_id: int | None = None
    resolved_option_code: str | None = None
    resolved_option_name: str | None = None
    acceptable_option_ids: tuple[int, ...] = ()
    avoided_option_ids: tuple[int, ...] = ()
    resolution_source: str = "not_applicable"
    effective_explicit_preference: float = 0.0
    option_explicitly_liked: bool = False
    effective_texture_score: float | None = None
    effective_convenience_score: float | None = None
    effective_ripe_storage_score: float | None = None


@dataclass(frozen=True, slots=True)
class PairSelection:
    """完整组合枚举后选出的两种水果及互补分。

    ``second_score`` 仍是第二个水果的单项 ``base_score``；``complement_score``
    是兼容命名，当前实际对应 ``nutrition_pair_score``。真正用于排序和
    持久化的 ``pair_score`` 还包含个体均值、感官类别差异和 pair novelty，
    因此不能用第二名单水果分替代组合分。
    """

    first: ScoredFruit
    second: ScoredFruit
    second_score: float
    complement_score: float
    pair_score: float = 0.0
    nutrition_pair_score: float = 0.0
    sensory_category_diversity: float = 0.0
    pair_novelty: float = 1.0
    near_top_count: int = 1


@dataclass(frozen=True, slots=True)
class RecommendationItemResult:
    """可持久化/返回 API 的单项推荐结果。

    ``score`` 当前由应用层写入该水果的单项分；``pair_score`` 和
    ``nutrition_pair_score`` 保存同一组合的上下文，供历史展示和审计使用。
    ``reasons`` 必须来自实际评分贡献或明确状态，不能为了填满条数而声称
    用户有不存在的偏好。
    """

    fruit: RecommendationFruit
    score: float
    rank: int
    reasons: tuple[RecommendationReason, ...]
    base_score: float
    complement_score: float | None = None
    individual_score: float | None = None
    pair_score: float | None = None
    nutrition_pair_score: float | None = None
    resolved_candidate: ResolvedFruitCandidate | None = None


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    """一次推荐必须恰好包含两个不同 rank 的水果。

    ``total_score`` 是选中组合的 ``pair_score``，不是概率或准确率；固定的
    两项 tuple 形状让 API、ORM 持久化和前端都能共享“两种水果”的合同。
    """

    items: tuple[RecommendationItemResult, RecommendationItemResult]
    total_score: float


__all__ = [
    "FruitPreference",
    "FeedbackEvent",
    "HistoryEvent",
    "NutritionProfile",
    "PairSelection",
    "RecommendationContext",
    "RecommendationFruit",
    "RecommendationItemResult",
    "RecommendationResult",
    "RecommendationUser",
    "ResolvedFruitCandidate",
    "SelectionOption",
    "SelectionOptionPreference",
    "ScoredFruit",
    "ScoreBreakdown",
    "SeasonEvaluation",
    "SeasonWindow",
]
