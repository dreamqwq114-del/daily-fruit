from app.models import Recommendation
from app.schemas.fruit import FruitDetail
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackRead,
    RecommendationItemDetail,
    RecommendationReason,
)


def recommendation_to_detail(
    recommendation: Recommendation,
) -> RecommendationDetail:
    items = []
    for item in sorted(recommendation.items, key=lambda value: value.rank):
        feedback = [
            RecommendationFeedbackRead.model_validate(value)
            for value in sorted(
                item.feedback,
                key=lambda value: (value.created_at, value.id),
            )
        ]
        items.append(
            RecommendationItemDetail(
                id=item.id,
                recommendation_id=item.recommendation_id,
                fruit_id=item.fruit_id,
                score=item.score,
                rank=item.rank,
                reasons=[
                    RecommendationReason.model_validate(reason)
                    for reason in item.reasons
                ],
                created_at=item.created_at,
                fruit=FruitDetail.model_validate(item.fruit),
                feedback=feedback,
            )
        )
    return RecommendationDetail(
        id=recommendation.id,
        user_id=recommendation.user_id,
        recommendation_date=recommendation.recommendation_date,
        refresh_number=recommendation.refresh_number,
        total_score=recommendation.total_score,
        status=recommendation.status,
        created_at=recommendation.created_at,
        items=items,
    )


__all__ = ["recommendation_to_detail"]
