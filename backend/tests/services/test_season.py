import pytest

from app.services import (
    InvalidRecommendationInputError,
    SeasonWindow,
    evaluate_season,
    month_is_in_range,
)


@pytest.mark.parametrize("month", [5, 6, 7, 8, 9])
def test_normal_month_range_includes_boundaries(month: int) -> None:
    assert month_is_in_range(month, 5, 9)


@pytest.mark.parametrize("month", [12, 1, 2, 3, 4])
def test_cross_year_range_includes_boundaries(month: int) -> None:
    assert month_is_in_range(month, 12, 4)


@pytest.mark.parametrize("month", [5, 10, 11])
def test_cross_year_range_rejects_outside_months(month: int) -> None:
    assert not month_is_in_range(month, 12, 4)


def test_season_uses_highest_matching_regional_score() -> None:
    result = evaluate_season(
        [
            SeasonWindow("全国", 5, 9, 0.8),
            SeasonWindow("华东", 6, 8, 0.95, region_level="area"),
            SeasonWindow("华南", 5, 10, 1.0, region_level="area"),
        ],
        region="华东",
        month=7,
    )

    assert result.has_relevant_data
    assert result.is_in_season
    assert result.score == pytest.approx(0.95)


def test_known_but_out_of_season_is_marked_inapplicable() -> None:
    result = evaluate_season(
        [SeasonWindow("全国", 5, 9, 0.9)],
        region="华东",
        month=11,
    )

    assert result.has_relevant_data
    assert not result.is_in_season
    assert result.score == 0.0


def test_missing_relevant_season_data_uses_penalty_not_exclusion() -> None:
    result = evaluate_season(
        [SeasonWindow("华南", 5, 9, 0.9, region_level="area")],
        region="华东",
        month=7,
    )

    assert not result.has_relevant_data
    assert not result.is_in_season
    assert result.score == pytest.approx(0.35)


@pytest.mark.parametrize("month", [0, 13])
def test_invalid_month_has_clear_error(month: int) -> None:
    with pytest.raises(InvalidRecommendationInputError, match="月份"):
        month_is_in_range(month, 1, 12)


@pytest.mark.parametrize(
    "season",
    [
        SeasonWindow("华东", 0, 12, 0.8),
        SeasonWindow("华东", 1, 13, 0.8),
        SeasonWindow("华东", 1, 12, 1.1),
        SeasonWindow("", 1, 12, 0.8),
    ],
)
def test_invalid_season_window_is_rejected_even_for_other_region(
    season: SeasonWindow,
) -> None:
    with pytest.raises(InvalidRecommendationInputError):
        evaluate_season([season], region="华南", month=7)
