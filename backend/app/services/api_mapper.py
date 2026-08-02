"""把推荐 ORM 图映射成不暴露 SQLAlchemy 对象的 API 响应。"""

from app.models import Recommendation
from app.schemas.fruit import FruitDetail, FruitFactRead
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackRead,
    RecommendationItemDetail,
    RecommendationReason,
)
from app.services.fruit_fact_service import select_daily_fact


def recommendation_to_detail(
    recommendation: Recommendation,
) -> RecommendationDetail:
    """稳定排序 items/feedback，并验证 JSONB reasons 的 Pydantic 结构。"""

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
                individual_score=item.individual_score,
                pair_score=item.pair_score,
                nutrition_pair_score=item.nutrition_pair_score,
                created_at=item.created_at,
                fruit=FruitDetail.model_validate(item.fruit),
                daily_fact=(
                    None
                    if (
                        daily_fact := select_daily_fact(
                            item.fruit.facts,
                            fruit_code=item.fruit.code,
                            recommendation_date=recommendation.recommendation_date,
                        )
                    )
                    is None
                    else FruitFactRead.model_validate(daily_fact)
                ),
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
