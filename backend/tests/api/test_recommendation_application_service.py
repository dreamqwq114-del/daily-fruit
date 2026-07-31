from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.errors import ResourceConflictError
from app.schemas.recommendation import RecommendationFeedbackCreate
from app.schemas.user import UserCreate
from app.services import recommendation_application_service, user_service


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
