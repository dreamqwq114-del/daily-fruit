"""把 ORM 对象映射为无数据库依赖的推荐输入类型。

mapper 不是无害的字段复制层，而是 ORM/数据库语义进入纯推荐领域对象
的边界：缺失值、旧字段和默认值会直接进入过滤与排序。这里不应引入
Session 查询或新的推荐规则；任何 fallback 都必须是中性/保守的，并在
数据迁移完成后重新评估是否可以移除。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from app.models import Fruit, User
from app.services.recommendation_types import (
    FeedbackEvent,
    FruitPreference,
    HistoryEvent,
    NutritionProfile,
    RecommendationContext,
    RecommendationFruit,
    RecommendationUser,
    SelectionOption,
    SelectionOptionPreference,
    SeasonWindow,
)


def user_to_recommendation_input(user: User) -> RecommendationUser:
    """提取推荐实际读取的用户字段；购买条件字段在此明确未接入。

    ``FruitPreference`` 的 ``None``、``False`` 和数值会原样保留，避免把
    未选择水果写成中性偏好。当前 ``market_access_level``、
    ``accepts_online_purchase`` 和 ``consumption_horizon_days`` 不属于
    RecommendationUser，因此保存它们不会改变本版本排序。
    """

    preferences = {
        item.fruit_id: FruitPreference(
            preference_score=(
                None
                if item.preference_score is None
                else float(item.preference_score)
            ),
            is_forbidden=item.is_forbidden,
            has_tried=item.has_tried,
            willing_to_try=item.willing_to_try,
        )
        for item in user.fruit_preferences
    }
    option_preferences: dict[int, tuple[SelectionOptionPreference, ...]] = {}
    grouped_options: dict[int, list[SelectionOptionPreference]] = {}
    for item in user.fruit_option_preferences:
        grouped_options.setdefault(item.fruit_id, []).append(
            SelectionOptionPreference(
                user_id=item.user_id,
                fruit_id=item.fruit_id,
                option_id=item.option_id,
                preference=item.preference,
            )
        )
    option_preferences = {
        fruit_id: tuple(items) for fruit_id, items in grouped_options.items()
    }
    return RecommendationUser(
        city=user.city,
        region=user.region,
        sweet_preference=(
            None if user.sweet_preference is None else float(user.sweet_preference)
        ),
        sour_preference=(
            None if user.sour_preference is None else float(user.sour_preference)
        ),
        soft_preference=(
            None if user.soft_preference is None else float(user.soft_preference)
        ),
        crisp_preference=(
            None if user.crisp_preference is None else float(user.crisp_preference)
        ),
        price_level=user.price_level,
        convenience_preference=float(user.convenience_preference),
        discovery_level=user.discovery_level,
        fruit_preferences=preferences,
        option_preferences=option_preferences,
    )


def fruit_to_recommendation_input(fruit: Fruit) -> RecommendationFruit:
    """复制水果、营养和季节快照，处理旧行缺失值并避免 N+1 查询。

    该函数假设 Repository 已经预加载 nutrition/seasons；它不补查数据库。
    营养缺失保留为 ``None``，表示未知；供应缺失使用 ``unknown``，不能
    乐观地当作 ``available``，因为后者会直接影响候选过滤与可得性分。
    """

    # 缺失营养留在 None，后续 normalization/pair complement 会降低 coverage
    # confidence，而不是把未知数据伪造成 0 分营养。
    nutrition = (
        None
        if fruit.nutrition is None
        else NutritionProfile(
            energy=float(fruit.nutrition.energy),
            vitamin_c=float(fruit.nutrition.vitamin_c),
            fiber=float(fruit.nutrition.fiber),
            potassium=float(fruit.nutrition.potassium),
            folate=float(fruit.nutrition.folate),
            carotenoids=float(fruit.nutrition.carotenoids),
        )
    )
    # 旧 season 行若没有新字段，使用保守的 national/0.45/unknown fallback。
    # 这些默认值是迁移兼容方案；数据迁移完整后应评估删除它们的必要性。
    seasons = tuple(
        SeasonWindow(
            region=item.region,
            start_month=item.start_month,
            end_month=item.end_month,
            season_score=float(item.season_score),
            region_level=(
                item.region_level
                if item.region_level is not None
                else "national"
            ),
            availability_score=float(
                item.availability_score
                if item.availability_score is not None
                else 0.45
            ),
            supply_status=(
                item.supply_status
                if item.supply_status is not None
                else "unknown"
            ),
        )
        for item in fruit.seasons
    )
    selection_options = tuple(
        SelectionOption(
            id=item.id,
            fruit_id=item.fruit_id,
            code=item.code,
            name=item.name,
            sweet_score=(
                None if item.sweet_score is None else float(item.sweet_score)
            ),
            sour_score=(
                None if item.sour_score is None else float(item.sour_score)
            ),
            soft_score=(
                None if item.soft_score is None else float(item.soft_score)
            ),
            crisp_score=(
                None if item.crisp_score is None else float(item.crisp_score)
            ),
            is_default=item.is_default,
            is_active=item.is_active,
            display_order=item.display_order,
            data_quality=item.data_quality,
            data_source_note=item.data_source_note,
        )
        for item in fruit.selection_options
    )
    return RecommendationFruit(
        id=fruit.id,
        name=fruit.name,
        code=fruit.code or "",
        aliases=tuple(fruit.aliases or ()),
        sweet_score=float(fruit.sweet_score),
        sour_score=float(fruit.sour_score),
        soft_score=float(fruit.soft_score),
        crisp_score=float(fruit.crisp_score),
        convenience_score=float(fruit.convenience_score),
        average_price_level=fruit.average_price_level,
        category=fruit.category,
        display_group=getattr(fruit, "display_group", "") or fruit.category,
        taste=fruit.taste,
        # 100g 只是在旧行缺失份量时的兼容元数据；当前 nutrition_demo 是
        # 无物理单位分数，份量换算不会因此变成真实营养计算。
        default_portion_grams=float(
            fruit.default_portion_grams
            if fruit.default_portion_grams is not None
            else 100
        ),
        direct_eating=fruit.direct_eating,
        consumption_mode=fruit.consumption_mode,
        daily_recommendation_role=fruit.daily_recommendation_role,
        preparation_difficulty=float(
            fruit.preparation_difficulty
            if fruit.preparation_difficulty is not None
            else 0.5
        ),
        portability_score=float(
            fruit.portability_score
            if fruit.portability_score is not None
            else 0.5
        ),
        messiness_score=float(
            fruit.messiness_score
            if fruit.messiness_score is not None
            else 0.5
        ),
        storage_difficulty=float(
            fruit.storage_difficulty
            if fruit.storage_difficulty is not None
            else 0.5
        ),
        aroma_intensity=float(
            fruit.aroma_intensity
            if fruit.aroma_intensity is not None
            else 0.5
        ),
        commonness_score=float(
            fruit.commonness_score
            if fruit.commonness_score is not None
            else 0.5
        ),
        novelty_level=(
            fruit.novelty_level if fruit.novelty_level is not None else 1
        ),
        data_quality=(
            fruit.data_quality if fruit.data_quality is not None else "low"
        ),
        data_source_note=fruit.data_source_note,
        is_active=fruit.is_active,
        nutrition=nutrition,
        seasons=seasons,
        selection_options=selection_options,
    )


def build_recommendation_context(
    *,
    month: int,
    today: date | None = None,
    recent_fruit_ids: Sequence[int] = (),
    feedback_by_fruit: Mapping[int, Sequence[str]] | None = None,
    history_events: Sequence[HistoryEvent] = (),
    feedback_events: Sequence[FeedbackEvent] = (),
    cooldown_pairs: Sequence[frozenset[int]] = (),
    previous_pairs: Sequence[frozenset[int]] = (),
    excluded_pair: frozenset[int] | None = None,
    allow_supporting: bool = False,
    random_seed: int | None = None,
) -> RecommendationContext:
    """把 Repository 查询结果规范化为一次纯算法计算的上下文。

    序列被固定成 tuple，映射值也固定成 tuple，保证算法输入不可变且不会
    被后续 ORM 生命周期影响。``feedback_by_fruit`` 是旧调用者兼容输入；
    新路径应同时提供带时间的 ``feedback_events``，这样反馈衰减才能使用
    真实事件时间。``excluded_pair``、``cooldown_pairs`` 和
    ``previous_pairs`` 的语义不同：前者是刷新硬排除，中者是短期组合冷却，
    后者只是长期组合新颖度信号。
    """

    return RecommendationContext(
        month=month,
        today=today,
        recent_fruit_ids=tuple(recent_fruit_ids),
        feedback_by_fruit={
            fruit_id: tuple(values)
            for fruit_id, values in (feedback_by_fruit or {}).items()
        },
        history_events=tuple(history_events),
        feedback_events=tuple(feedback_events),
        cooldown_pairs=tuple(cooldown_pairs),
        previous_pairs=tuple(previous_pairs),
        excluded_pair=excluded_pair,
        allow_supporting=allow_supporting,
        random_seed=random_seed,
    )


__all__ = [
    "build_recommendation_context",
    "fruit_to_recommendation_input",
    "user_to_recommendation_input",
]
