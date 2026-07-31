from decimal import Decimal

from app.models import (
    Fruit,
    FruitNutrition,
    FruitSeason,
    User,
    UserFruitPreference,
)
from app.services.recommendation_mapper import (
    build_recommendation_context,
    fruit_to_recommendation_input,
    user_to_recommendation_input,
)


def test_mapper_converts_loaded_orm_graph_without_session() -> None:
    user = User(
        id=1,
        username="小果",
        city="苏州",
        region="华东",
        sweet_preference=Decimal("0.8"),
        sour_preference=Decimal("0.2"),
        soft_preference=Decimal("0.4"),
        crisp_preference=Decimal("0.9"),
        price_level=2,
        convenience_preference=Decimal("0.7"),
    )
    user.fruit_preferences = [
        UserFruitPreference(
            fruit_id=3,
            preference_score=Decimal("2"),
            is_forbidden=False,
        )
    ]
    fruit = Fruit(
        id=3,
        name="苹果",
        category="仁果",
        taste="清甜脆爽",
        sweet_score=Decimal("0.7"),
        sour_score=Decimal("0.3"),
        soft_score=Decimal("0.2"),
        crisp_score=Decimal("0.9"),
        convenience_score=Decimal("0.8"),
        average_price_level=2,
        default_portion="1个",
        description="测试水果",
        is_active=True,
    )
    fruit.nutrition = FruitNutrition(
        energy=Decimal("0.2"),
        vitamin_c=Decimal("0.3"),
        fiber=Decimal("0.4"),
        potassium=Decimal("0.5"),
        folate=Decimal("0.6"),
        carotenoids=Decimal("0.7"),
    )
    fruit.seasons = [
        FruitSeason(
            region="华东",
            start_month=8,
            end_month=12,
            season_score=Decimal("0.95"),
            availability_score=Decimal("0"),
        )
    ]

    mapped_user = user_to_recommendation_input(user)
    mapped_fruit = fruit_to_recommendation_input(fruit)

    assert mapped_user.fruit_preferences[3].preference_score == 2
    assert mapped_fruit.nutrition is not None
    assert mapped_fruit.nutrition.folate == 0.6
    assert mapped_fruit.seasons[0].season_score == 0.95
    assert mapped_fruit.seasons[0].availability_score == 0


def test_mapper_preserves_explicit_zero_v2_identity_values() -> None:
    fruit = Fruit(
        id=9,
        code="zero-values",
        name="zero fruit",
        category="test",
        taste="test",
        sweet_score=Decimal("0"),
        sour_score=Decimal("0"),
        soft_score=Decimal("0"),
        crisp_score=Decimal("0"),
        convenience_score=Decimal("0"),
        average_price_level=1,
        default_portion="100 g",
        default_portion_grams=Decimal("1"),
        direct_eating=False,
        consumption_mode="ingredient",
        daily_recommendation_role="supporting",
        preparation_difficulty=Decimal("0"),
        portability_score=Decimal("0"),
        messiness_score=Decimal("0"),
        storage_difficulty=Decimal("0"),
        aroma_intensity=Decimal("0"),
        commonness_score=Decimal("0"),
        novelty_level=0,
        data_quality="low",
        description="test",
    )
    mapped = fruit_to_recommendation_input(fruit)
    assert mapped.default_portion_grams == 1
    assert mapped.preparation_difficulty == 0
    assert mapped.portability_score == 0
    assert mapped.messiness_score == 0
    assert mapped.storage_difficulty == 0
    assert mapped.aroma_intensity == 0
    assert mapped.commonness_score == 0
    assert mapped.novelty_level == 0


def test_context_mapper_copies_mutable_inputs() -> None:
    feedback = {1: ["liked"]}
    recent = [1, 2]

    context = build_recommendation_context(
        month=7,
        recent_fruit_ids=recent,
        feedback_by_fruit=feedback,
        random_seed=42,
    )
    feedback[1].append("eaten")
    recent.append(3)

    assert context.recent_fruit_ids == (1, 2)
    assert context.feedback_by_fruit == {1: ("liked",)}
    assert context.random_seed == 42
