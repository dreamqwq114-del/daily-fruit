"""消费类型的跨层公开策略。

这里仅维护父水果使用哪一种匹配方式，不读取数据库，也不计算推荐分。
API 展示与推荐核心共同依赖这份映射，避免前端根据可空覆盖字段猜测。
"""

from typing import Literal


SelectionMatchingMode = Literal["texture", "sweet-sour", "explicit-only"]
SelectionOptionScoreEffect = Literal["profile-override", "filter-only"]

MATCHING_DIMENSIONS_BY_FRUIT_CODE: dict[str, tuple[str, ...]] = {
    "peach": ("texture_score",),
    "kiwifruit": ("sweet_score", "sour_score"),
    "apple": ("texture_score",),
    "grape": ("texture_score",),
}

EXPLICIT_ONLY_OPTION_FRUITS = frozenset({"pomegranate"})


def matching_dimensions_for_code(code: str) -> tuple[str, ...]:
    return MATCHING_DIMENSIONS_BY_FRUIT_CODE.get(code, ())


def selection_matching_mode_for_code(code: str) -> SelectionMatchingMode:
    dimensions = matching_dimensions_for_code(code)
    if dimensions == ("texture_score",):
        return "texture"
    if dimensions == ("sweet_score", "sour_score"):
        return "sweet-sour"
    return "explicit-only"


def selection_option_score_effect_for_code(code: str) -> SelectionOptionScoreEffect:
    return "filter-only" if code in EXPLICIT_ONLY_OPTION_FRUITS else "profile-override"


__all__ = [
    "EXPLICIT_ONLY_OPTION_FRUITS",
    "MATCHING_DIMENSIONS_BY_FRUIT_CODE",
    "SelectionMatchingMode",
    "SelectionOptionScoreEffect",
    "matching_dimensions_for_code",
    "selection_matching_mode_for_code",
    "selection_option_score_effect_for_code",
]
