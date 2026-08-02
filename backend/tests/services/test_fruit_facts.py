from datetime import date

from app.models import FruitFact
from app.services.fruit_fact_service import select_daily_fact


def fact(fact_id: int, sort_order: int, *, is_active: bool = True) -> FruitFact:
    return FruitFact(
        id=fact_id,
        fruit_id=22,
        fact_type="botany",
        fact_text=f"fact-{sort_order}",
        sort_order=sort_order,
        is_active=is_active,
    )


def test_daily_fact_is_stable_for_same_fruit_and_date() -> None:
    facts = [fact(1, 1), fact(2, 2), fact(3, 3)]

    first = select_daily_fact(
        facts,
        fruit_code="durian",
        recommendation_date=date(2026, 8, 3),
    )
    second = select_daily_fact(
        facts,
        fruit_code="durian",
        recommendation_date=date(2026, 8, 3),
    )

    assert first is not None
    assert second is not None
    assert first.sort_order == second.sort_order


def test_daily_fact_rotates_by_sort_order_on_next_date() -> None:
    facts = [fact(1, 1), fact(2, 2), fact(3, 3)]
    today = select_daily_fact(
        facts,
        fruit_code="durian",
        recommendation_date=date(2026, 8, 3),
    )
    tomorrow = select_daily_fact(
        facts,
        fruit_code="durian",
        recommendation_date=date(2026, 8, 4),
    )

    assert today is not None
    assert tomorrow is not None
    assert tomorrow.sort_order == (today.sort_order % 3) + 1


def test_inactive_and_empty_facts_are_not_selected() -> None:
    assert (
        select_daily_fact(
            [fact(1, 1, is_active=False)],
            fruit_code="durian",
            recommendation_date=date(2026, 8, 3),
        )
        is None
    )
