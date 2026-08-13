from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.errors import ResourceConflictError
from app.schemas.recommendation import RecommendationFeedbackCreate
from app.schemas.user import UserCreate, UserFruitPreferencesUpdate
from app.services import (
    NoRecommendationCandidatesError,
    recommendation_application_service,
    user_service,
)


TODAY = date(2026, 7, 31)


def create_user(session: Session):
    return user_service.create_user(
        session,
        UserCreate(
            username="推荐事务测试",
            city="苏州",
            region="华东",
            sweet_preference="0.8",
            sour_preference="0.3",
            soft_preference="0.4",
            crisp_preference="0.8",
            price_level=2,
            convenience_preference="0.8",
        ),
    )


def test_today_is_persisted_and_reused(api_session: Session) -> None:
    user = create_user(api_session)

    first = recommendation_application_service.get_today_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )
    second = recommendation_application_service.get_today_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )

    assert first.id == second.id
    assert first.status == "active"
    assert first.refresh_number == 0
    assert len(first.items) == 2
    assert len({item.fruit_id for item in first.items}) == 2


def test_real_dragon_fruit_option_is_mapped_and_frozen_in_history(
    api_session: Session,
) -> None:
    user = create_user(api_session)
    fruit_rows = api_session.execute(
        text("SELECT id, code FROM public.fruits WHERE is_active")
    ).all()
    fruit_ids = {code: fruit_id for fruit_id, code in fruit_rows}
    white_option_id = api_session.execute(
        text(
            """
            SELECT option_row.id
            FROM public.fruit_selection_options AS option_row
            JOIN public.fruits AS fruit ON fruit.id = option_row.fruit_id
            WHERE fruit.code='dragon_fruit' AND option_row.code='white'
            """
        )
    ).scalar_one()
    payload = UserFruitPreferencesUpdate.model_validate(
        {
            "preferences": [
                {
                    "fruit_id": fruit_id,
                    "is_forbidden": code not in {"apple", "dragon_fruit"},
                }
                for fruit_id, code in fruit_rows
            ],
            "option_preferences": [
                {
                    "fruit_id": fruit_ids["dragon_fruit"],
                    "option_id": white_option_id,
                    "preference": "liked",
                }
            ],
        }
    )
    user_service.replace_fruit_preferences(api_session, user.id, payload)

    recommendation = recommendation_application_service.get_today_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )
    assert {item.fruit_id for item in recommendation.items} == {
        fruit_ids["apple"],
        fruit_ids["dragon_fruit"],
    }
    persisted = api_session.execute(
        text(
            """
            SELECT fruit_snapshot, selection_option_code_snapshot,
                   selection_resolution_source,
                   effective_sour_score_snapshot,
                   effective_texture_score_snapshot
            FROM public.recommendation_items
            WHERE recommendation_id=:recommendation_id
              AND fruit_id=:fruit_id
            """
        ),
        {
            "recommendation_id": recommendation.id,
            "fruit_id": fruit_ids["dragon_fruit"],
        },
    ).one()

    assert persisted.fruit_snapshot["selection_matching_mode"] == "explicit-only"
    assert persisted.fruit_snapshot["selection_option_score_effect"] == (
        "profile-override"
    )
    assert persisted.selection_option_code_snapshot == "white"
    assert persisted.selection_resolution_source == "explicit"
    assert float(persisted.effective_sour_score_snapshot) == pytest.approx(0.05)
    assert float(persisted.effective_texture_score_snapshot) == pytest.approx(0.40)


def test_refresh_replaces_old_group_and_records_event(
    api_session: Session,
) -> None:
    user = create_user(api_session)
    first = recommendation_application_service.get_today_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )

    refreshed = recommendation_application_service.refresh_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )
    history = recommendation_application_service.list_recommendation_history(
        api_session,
        user.id,
    )

    assert refreshed.id != first.id
    assert refreshed.refresh_number == 1
    assert refreshed.status == "active"
    assert {item.fruit_id for item in refreshed.items} != {
        item.fruit_id for item in first.items
    }
    assert [item.status for item in history] == ["active", "replaced"]
    replaced = history[1]
    assert any(
        feedback.feedback_type == "change_requested"
        for item in replaced.items
        for feedback in item.feedback
    )


def test_feedback_is_idempotent_and_appears_in_history(
    api_session: Session,
) -> None:
    user = create_user(api_session)
    recommendation = (
        recommendation_application_service.get_today_recommendation(
            api_session,
            user.id,
            today=TODAY,
        )
    )
    item_id = recommendation.items[0].id
    payload = RecommendationFeedbackCreate(
        feedback_type="liked",
        comment="不错",
    )

    first = recommendation_application_service.submit_feedback(
        api_session,
        item_id,
        payload,
    )
    second = recommendation_application_service.submit_feedback(
        api_session,
        item_id,
        payload,
    )
    history = recommendation_application_service.list_recommendation_history(
        api_session,
        user.id,
    )

    assert first.created
    assert not second.created
    assert first.feedback.id == second.feedback.id
    assert history[0].items[0].feedback[0].feedback_type == "liked"


def test_refresh_requires_existing_active_recommendation(
    api_session: Session,
) -> None:
    user = create_user(api_session)

    with pytest.raises(ResourceConflictError, match="active"):
        recommendation_application_service.refresh_recommendation(
            api_session,
            user.id,
            today=TODAY,
        )


def test_failed_refresh_keeps_original_recommendation_active(
    api_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user(api_session)
    first = recommendation_application_service.get_today_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )

    def fail_recommendation(*args: object, **kwargs: object) -> None:
        raise NoRecommendationCandidatesError(
            "当前没有其他满足条件的水果组合"
        )

    monkeypatch.setattr(
        recommendation_application_service,
        "recommend_fruits",
        fail_recommendation,
    )

    with pytest.raises(ResourceConflictError, match="当前没有其他"):
        recommendation_application_service.refresh_recommendation(
            api_session,
            user.id,
            today=TODAY,
        )

    # Service 抛错后由请求 Session 边界回滚；模拟该边界后，旧 active 必须保留。
    api_session.rollback()
    current = recommendation_application_service.get_today_recommendation(
        api_session,
        user.id,
        today=TODAY,
    )
    history = recommendation_application_service.list_recommendation_history(
        api_session,
        user.id,
    )

    assert current.id == first.id
    assert current.status == "active"
    assert len(history) == 1
