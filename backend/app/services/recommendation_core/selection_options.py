"""父水果消费类型的确定性解析。

本模块只把父水果、选项和用户偏好解析成一个真实可购买的口感档案。
它不访问数据库，也不计算季节、营养、价格、历史或组合分数。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from app.services.recommendation_types import (
    FruitPreference,
    RecommendationFruit,
    RecommendationUser,
    ResolvedFruitCandidate,
    SelectionOption,
    SelectionOptionPreference,
)

from .common import InvalidRecommendationInputError, clamp_score


# matching_dimensions 是父水果的消费体验配置，不是数据库中的新全局评分字段。
MATCHING_DIMENSIONS: Mapping[str, tuple[str, ...]] = {
    "peach": ("soft_score", "crisp_score"),
    "kiwifruit": ("sweet_score", "sour_score"),
}


def matching_dimensions_for(fruit: RecommendationFruit) -> tuple[str, ...]:
    """返回同一父水果所有兄弟选项共同使用的匹配维度。"""

    return MATCHING_DIMENSIONS.get(fruit.code, ())


def _complete_option_scores(
    fruit: RecommendationFruit,
    option: SelectionOption,
) -> tuple[float, float, float, float]:
    """将 NULL 维度继承父水果值，不对兄弟选项做平均。"""

    values = (
        option.sweet_score
        if option.sweet_score is not None
        else fruit.sweet_score,
        option.sour_score
        if option.sour_score is not None
        else fruit.sour_score,
        option.soft_score
        if option.soft_score is not None
        else fruit.soft_score,
        option.crisp_score
        if option.crisp_score is not None
        else fruit.crisp_score,
    )
    return tuple(clamp_score(float(value)) for value in values)  # type: ignore[return-value]


def _taste_match_for_option(
    fruit: RecommendationFruit,
    option: SelectionOption,
    user: RecommendationUser,
) -> float:
    """复用推荐核心现有的 target * value 匹配语义。"""

    values = _complete_option_scores(fruit, option)
    by_name = dict(zip(("sweet_score", "sour_score", "soft_score", "crisp_score"), values))
    configured = []
    for dimension in matching_dimensions_for(fruit):
        target = getattr(user, dimension.replace("_score", "_preference"), None)
        if target is not None:
            value = by_name[dimension]
            configured.append(
                float(target) * value + (1 - float(target)) * (1 - value)
            )
    return clamp_score(sum(configured) / len(configured)) if configured else 0.5


def _option_preferences_for(
    fruit_id: int,
    preferences: Mapping[int, Sequence[SelectionOptionPreference]],
) -> dict[int, str]:
    """读取当前父水果的类型偏好，并拒绝跨父水果污染。"""

    result: dict[int, str] = {}
    for item in preferences.get(fruit_id, ()):
        if item.fruit_id != fruit_id:
            raise InvalidRecommendationInputError("消费类型偏好与父水果不匹配")
        if item.preference not in {"liked", "disliked"}:
            raise InvalidRecommendationInputError("消费类型偏好无效")
        result[item.option_id] = item.preference
    return result


def resolve_selection_option(
    fruit: RecommendationFruit,
    active_options: Iterable[SelectionOption] | None = None,
    parent_preference: FruitPreference | None = None,
    option_preferences: Sequence[SelectionOptionPreference] = (),
    user: RecommendationUser | None = None,
) -> ResolvedFruitCandidate | None:
    """为一个父水果确定唯一消费类型。

    选项优先级是明确 liked > disliked 排除 > 父级态度 > 全局口味 > default。
    unknown 不会被当作 liked；推断结果不会写回偏好表，也不会使用随机数。
    """

    options = tuple(
        sorted(
            (item for item in (active_options or ()) if item.is_active),
            key=lambda item: (item.display_order, item.id),
        )
    )
    if not options:
        if parent_preference is not None and (
            parent_preference.is_forbidden
            or parent_preference.preference_score is not None
            and float(parent_preference.preference_score) <= -1
        ):
            return None
        return ResolvedFruitCandidate(
            fruit=fruit,
            effective_sweet_score=fruit.sweet_score,
            effective_sour_score=fruit.sour_score,
            effective_soft_score=fruit.soft_score,
            effective_crisp_score=fruit.crisp_score,
        )

    if user is None:
        raise InvalidRecommendationInputError("解析消费类型需要用户画像")
    preference_by_option = _option_preferences_for(
        fruit.id,
        {fruit.id: tuple(option_preferences)},
    )
    disliked_ids = {
        option_id
        for option_id, preference in preference_by_option.items()
        if preference == "disliked"
    }
    liked_ids = {
        option_id
        for option_id, preference in preference_by_option.items()
        if preference == "liked"
    }
    option_ids = {option.id for option in options}
    liked_ids &= option_ids
    disliked_ids &= option_ids
    allowed = [option for option in options if option.id not in disliked_ids]
    if liked_ids:
        allowed = [option for option in allowed if option.id in liked_ids]

    if parent_preference is not None and parent_preference.is_forbidden:
        return None
    parent_disliked = parent_preference is not None and (
        parent_preference.preference_score is not None
        and float(parent_preference.preference_score) <= -1
    )
    if parent_disliked and not liked_ids:
        return None
    if not allowed:
        return None

    configured = any(
        getattr(user, dimension.replace("_score", "_preference"), None) is not None
        for dimension in matching_dimensions_for(fruit)
    )
    if liked_ids:
        source = "explicit"
        chosen = max(
            allowed,
            key=lambda option: (
                _taste_match_for_option(fruit, option, user) if configured else 0.0,
                -option.display_order,
                -option.id,
            ),
        )
        effective_explicit = 1.0
    elif configured:
        source = "inferred_from_global_preference"
        chosen = max(
            allowed,
            key=lambda option: (
                _taste_match_for_option(fruit, option, user),
                -option.display_order,
                -option.id,
            ),
        )
        effective_explicit = 0.0
    else:
        source = "default"
        chosen = next((option for option in allowed if option.is_default), allowed[0])
        effective_explicit = 0.0

    sweet, sour, soft, crisp = _complete_option_scores(fruit, chosen)
    acceptable = tuple(sorted(liked_ids - {chosen.id}))
    avoided = tuple(sorted(disliked_ids))
    return ResolvedFruitCandidate(
        fruit=fruit,
        effective_sweet_score=sweet,
        effective_sour_score=sour,
        effective_soft_score=soft,
        effective_crisp_score=crisp,
        resolved_option_id=chosen.id,
        resolved_option_code=chosen.code,
        resolved_option_name=chosen.name,
        acceptable_option_ids=acceptable,
        avoided_option_ids=avoided,
        resolution_source=source,
        effective_explicit_preference=effective_explicit,
        option_explicitly_liked=bool(liked_ids),
    )


def resolve_fruit_candidate(
    fruit: RecommendationFruit,
    user: RecommendationUser,
) -> ResolvedFruitCandidate | None:
    """从领域对象中解析当前父水果，供评分循环只调用一次。"""

    return resolve_selection_option(
        fruit,
        fruit.selection_options,
        user.fruit_preferences.get(fruit.id),
        user.option_preferences.get(fruit.id, ()),
        user=user,
    )


__all__ = [
    "MATCHING_DIMENSIONS",
    "matching_dimensions_for",
    "resolve_fruit_candidate",
    "resolve_selection_option",
]
