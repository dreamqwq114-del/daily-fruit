from datetime import date
from types import SimpleNamespace

import pytest

from app.services import recommendation_application_service as service


def _fake_result(*fruit_ids: int) -> SimpleNamespace:
    return SimpleNamespace(
        items=tuple(
            SimpleNamespace(fruit=SimpleNamespace(id=fruit_id))
            for fruit_id in fruit_ids
        ),
        total_score=0.5,
    )


def _stub_recommendation_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """隔离数据库映射，只测试应用层对推荐核心的调用合同。"""

    monkeypatch.setattr(
        service.fruit_repository,
        "list_active_fruits",
        lambda session: ["fruit-1", "fruit-2"],
    )
    monkeypatch.setattr(
        service,
        "fruit_to_recommendation_input",
        lambda fruit: fruit,
    )
    monkeypatch.setattr(
        service,
        "user_to_recommendation_input",
        lambda user: "domain-user",
    )
    monkeypatch.setattr(
        service.recommendation_repository,
        "recent_fruit_ids",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        service.recommendation_repository,
        "history_events",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        service.recommendation_repository,
        "previous_pairs",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        service.recommendation_repository,
        "feedback_events",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        service.recommendation_repository,
        "feedback_by_fruit",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        service,
        "build_recommendation_context",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )


def test_application_service_does_not_retry_with_modified_fruit_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_recommendation_inputs(monkeypatch)
    calls: list[tuple[object, ...]] = []

    def fake_recommend(fruits, user, context):
        calls.append(tuple(fruits))
        return _fake_result(1, 2)

    monkeypatch.setattr(service, "recommend_fruits", fake_recommend)

    with pytest.raises(service.RecommendationInvariantError):
        service._calculate_recommendation(
            object(),
            SimpleNamespace(id=7),
            date(2026, 8, 10),
            refresh_number=1,
            previous_ids={1, 2},
        )

    assert calls == [("fruit-1", "fruit-2")]


def test_application_invariant_check_is_skipped_for_initial_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_recommendation_inputs(monkeypatch)
    result = _fake_result(1, 2)
    calls = 0

    def fake_recommend(fruits, user, context):
        nonlocal calls
        calls += 1
        return result

    monkeypatch.setattr(service, "recommend_fruits", fake_recommend)

    actual = service._calculate_recommendation(
        object(),
        SimpleNamespace(id=7),
        date(2026, 8, 10),
        refresh_number=0,
    )

    assert actual is result
    assert calls == 1


def test_persistence_rejects_results_without_frozen_fruit_context() -> None:
    with pytest.raises(
        service.RecommendationInvariantError,
        match="未加载快照上下文",
    ):
        service._persist_recommendation(
            object(),
            user_id=7,
            recommendation_date=date(2026, 8, 10),
            refresh_number=0,
            result=_fake_result(1, 2),
            fruits=(),
        )
