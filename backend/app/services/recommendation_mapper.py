"""把 ORM 对象映射为无数据库依赖的推荐输入类型。"""

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
    SeasonWindow,
)


def user_to_recommendation_input(user: User) -> RecommendationUser:
    """提取推荐实际读取的用户字段；购买条件字段在此明确未接入。"""

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
    )


def fruit_to_recommendation_input(fruit: Fruit) -> RecommendationFruit:
    """复制水果、营养和季节快照，处理旧行缺失值并避免 N+1 查询。"""

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
        taste=fruit.taste,
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
    )


def build_recommendation_context(
    *,
    month: int,
    today: date | None = None,
    recent_fruit_ids: Sequence[int] = (),
    feedback_by_fruit: Mapping[int, Sequence[str]] | None = None,
    history_events: Sequence[HistoryEvent] = (),
    feedback_events: Sequence[FeedbackEvent] = (),
    previous_pairs: Sequence[frozenset[int]] = (),
    excluded_pair: frozenset[int] | None = None,
    allow_supporting: bool = False,
    random_seed: int | None = None,
) -> RecommendationContext:
    """把 Repository 查询结果规范化为一次纯算法计算的上下文。"""

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
