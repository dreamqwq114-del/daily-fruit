"""推荐算法共享的异常与基础分数工具。"""

from __future__ import annotations

import math
from collections.abc import Mapping


class RecommendationError(Exception):
    """Base class for understandable recommendation domain errors."""


class InvalidRecommendationInputError(RecommendationError):
    """Raised when data passed to the pure algorithm is invalid."""


class NoRecommendationCandidatesError(RecommendationError):
    """Raised when fewer than two eligible fruits remain."""


def clamp_score(value: float) -> float:
    """将分数限制在 [0, 1]，同时拒绝 NaN/无穷值。"""

    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidRecommendationInputError("分数必须是有限数值")
    return min(1.0, max(0.0, numeric))


def _validate_unit_scores(values: Mapping[str, float | None]) -> None:
    """验证可选的单位区间分数；``None`` 表示未提供，不代表 0。"""

    for name, value in values.items():
        if value is None:
            continue
        numeric = float(value)
        if not math.isfinite(numeric) or not 0 <= numeric <= 1:
            raise InvalidRecommendationInputError(
                f"{name} 必须在 0 到 1 之间"
            )


__all__ = [
    "InvalidRecommendationInputError",
    "NoRecommendationCandidatesError",
    "RecommendationError",
    "clamp_score",
]
