"""把推荐 ORM 图映射成不暴露 SQLAlchemy 对象的 API 响应。"""

from app.models import Recommendation
from app.schemas.fruit import FruitDetail, FruitFactRead
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationFeedbackRead,
    RecommendationItemDetail,
    RecommendationReason,
    RecommendationSelectionOptionRead,
    RecommendationSelectionRead,
    RecommendationSnapshotRead,
)
def recommendation_to_detail(
    recommendation: Recommendation,
) -> RecommendationDetail:
    """稳定排序 items/feedback，并验证 JSONB reasons 的 Pydantic 结构。"""

    items = []
    for item in sorted(recommendation.items, key=lambda value: value.rank):
        fruit_detail = FruitDetail.model_validate(item.fruit_snapshot)
        daily_fact_snapshot = getattr(item, "daily_fact_snapshot", None)
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
                selection=(
                    None
                    if item.selection_option_id is None
                    else RecommendationSelectionRead(
                        resolution_source=(
                            item.selection_resolution_source or "default"
                        ),
                        resolved_option=RecommendationSelectionOptionRead(
                            id=item.selection_option_id,
                            code=(
                                item.selection_option_code_snapshot
                                or "unknown"
                            ),
                            name=(
                                item.selection_option_name_snapshot
                                or "未命名类型"
                            ),
                        ),
                    )
                ),
                snapshot=(
                    RecommendationSnapshotRead(
                        effective_sweet_score=item.effective_sweet_score_snapshot,
                        effective_sour_score=item.effective_sour_score_snapshot,
                        effective_texture_score=getattr(
                            item, "effective_texture_score_snapshot", None
                        ),
                        effective_convenience_score=getattr(
                            item, "effective_convenience_score_snapshot", None
                        ),
                        effective_ripe_storage_score=getattr(
                            item, "effective_ripe_storage_score_snapshot", None
                        ),
                    )
                    if any(
                        getattr(item, field, None) is not None
                        for field in (
                            "effective_sweet_score_snapshot",
                            "effective_sour_score_snapshot",
                            "effective_texture_score_snapshot",
                            "effective_convenience_score_snapshot",
                            "effective_ripe_storage_score_snapshot",
                        )
                    )
                    else None
                ),
                created_at=item.created_at,
                fruit=fruit_detail,
                daily_fact=(
                    FruitFactRead.model_validate(daily_fact_snapshot)
                    if daily_fact_snapshot is not None
                    else None
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
        scoring_model_version=getattr(recommendation, "scoring_model_version", None),
        fruit_profile_version=getattr(recommendation, "fruit_profile_version", None),
        created_at=recommendation.created_at,
        items=items,
    )


__all__ = ["recommendation_to_detail"]
