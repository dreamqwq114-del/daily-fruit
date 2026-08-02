"""冷知识选择服务。

冷知识只负责展示，不参与候选过滤、评分、营养互补或推荐理由生成。
同一种水果在同一天使用稳定的 ``sort_order``，页面刷新和主动换组不会
随机改变已经看到的文案；日期变化时按顺序轮换到下一条。
"""

from __future__ import annotations

from datetime import date
from collections.abc import Sequence

from app.models.fruit import FruitFact


def _fruit_code_offset(fruit_code: str) -> int:
    """用稳定的字符串偏移替代 Python ``hash``，避免进程间随机化。"""

    return sum((index + 1) * ord(char) for index, char in enumerate(fruit_code))


def select_daily_fact(
    facts: Sequence[FruitFact],
    *,
    fruit_code: str,
    recommendation_date: date,
) -> FruitFact | None:
    """按水果 code 和推荐日期确定性选择当天的一条冷知识。"""

    active_facts = sorted(
        (fact for fact in facts if fact.is_active),
        key=lambda fact: (fact.sort_order, fact.id),
    )
    if not active_facts:
        return None

    index = (
        recommendation_date.toordinal() + _fruit_code_offset(fruit_code)
    ) % len(active_facts)
    return active_facts[index]


__all__ = ["select_daily_fact"]
