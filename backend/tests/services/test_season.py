import pytest

from app.services import (
    InvalidRecommendationInputError,
    SeasonWindow,
    evaluate_season,
    month_is_in_range,
)


def evidenced_harvest(
    region: str,
    start_month: int,
    end_month: int,
    season_score: float,
    *,
    region_level: str = "national",
) -> SeasonWindow:
    return SeasonWindow(
        region,
        start_month,
        end_month,
        season_score,
        region_level=region_level,
        data_quality="high",
        source_note="test harvest evidence",
        source_year=2026,
        is_scoring_enabled=True,
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


def test_harvest_season_uses_best_matching_evidence_across_production_regions() -> None:
    result = evaluate_season(
        [
            evidenced_harvest("全国", 5, 9, 0.8),
            evidenced_harvest("华东", 6, 8, 0.95, region_level="area"),
            evidenced_harvest("华南", 5, 10, 1.0, region_level="area"),
        ],
        region="华东",
        month=7,
    )

    assert result.has_relevant_data
    assert result.is_in_season
    assert result.score == pytest.approx(1.0)
    assert result.has_harvest_data
    assert not result.has_market_data
    assert result.used_market_fallback


def test_known_but_out_of_season_is_marked_inapplicable() -> None:
    result = evaluate_season(
        [evidenced_harvest("全国", 5, 9, 0.9)],
        region="华东",
        month=11,
    )

    assert result.has_relevant_data
    assert not result.is_in_season
    assert result.score == 0.0


def test_missing_relevant_season_data_uses_penalty_not_exclusion() -> None:
    result = evaluate_season(
        [
            SeasonWindow(
                "华南",
                5,
                9,
                0.9,
                region_level="area",
                data_quality="unverified",
                is_scoring_enabled=False,
            )
        ],
        region="华东",
        month=7,
    )

    assert not result.has_relevant_data
    assert not result.is_in_season
    assert result.score == pytest.approx(0.35)


def test_market_window_falls_back_to_matching_national_month() -> None:
    result = evaluate_season(
        [
            SeasonWindow(
                "华东",
                1,
                3,
                0.35,
                region_level="area",
                availability_score=0.9,
                supply_status="available",
                data_scope="market",
                data_quality="high",
                source_note="test area market evidence",
                source_year=2026,
                is_scoring_enabled=True,
            ),
            SeasonWindow(
                "全国",
                1,
                12,
                0.35,
                availability_score=0.7,
                supply_status="available",
                data_scope="market",
                data_quality="medium",
                source_note="test national market evidence",
                source_year=2026,
                is_scoring_enabled=True,
            ),
        ],
        region="华东",
        month=7,
    )

    assert result.availability_score == pytest.approx(0.7)
    assert result.supply_status == "available"
    assert result.region_rank == 1
    assert result.used_market_fallback
    assert not result.market_region_matched
    assert not result.market_reason_eligible


def test_source_backed_area_market_window_can_support_local_reason() -> None:
    result = evaluate_season(
        [
            SeasonWindow(
                "华东",
                1,
                12,
                0.35,
                region_level="area",
                availability_score=0.9,
                supply_status="available",
                data_scope="market",
                data_quality="medium",
                source_note="test area market evidence",
                source_year=2026,
                is_scoring_enabled=True,
            )
        ],
        region="华东",
        month=7,
    )

    assert result.market_region_matched
    assert not result.used_market_fallback
    assert result.market_reason_eligible


def test_overlapping_market_windows_are_order_independent_and_conservative() -> None:
    unavailable = SeasonWindow(
        "华东",
        6,
        8,
        0.35,
        region_level="area",
        availability_score=0.0,
        supply_status="unavailable",
        data_scope="market",
        data_quality="high",
        source_note="test unavailable evidence",
        source_year=2026,
        is_scoring_enabled=True,
    )
    available = SeasonWindow(
        "华东",
        1,
        12,
        0.35,
        region_level="area",
        availability_score=0.9,
        supply_status="available",
        data_scope="market",
        data_quality="high",
        source_note="test available evidence",
        source_year=2026,
        is_scoring_enabled=True,
    )

    forward = evaluate_season(
        [unavailable, available], region="华东", month=7
    )
    reverse = evaluate_season(
        [available, unavailable], region="华东", month=7
    )

    assert forward == reverse
    assert forward.supply_status == "unavailable"
    assert forward.availability_score == 0.0


def test_higher_quality_market_evidence_wins_before_availability_score() -> None:
    high_unavailable = SeasonWindow(
        "华东",
        1,
        12,
        0.35,
        region_level="area",
        availability_score=0.0,
        supply_status="unavailable",
        data_scope="market",
        data_quality="high",
        source_note="test high-quality evidence",
        source_year=2026,
        is_scoring_enabled=True,
    )
    medium_available = SeasonWindow(
        "华东",
        1,
        6,
        0.35,
        region_level="area",
        availability_score=0.9,
        supply_status="available",
        data_scope="market",
        data_quality="medium",
        source_note="test medium-quality evidence",
        source_year=2026,
        is_scoring_enabled=True,
    )

    result = evaluate_season(
        [medium_available, high_unavailable], region="华东", month=6
    )

    assert result.supply_status == "unavailable"
    assert result.availability_score == 0.0


def test_enabled_window_without_medium_or_high_evidence_is_rejected() -> None:
    unsupported = SeasonWindow(
        "全国",
        1,
        12,
        0.9,
        data_quality="low",
        is_scoring_enabled=True,
    )

    with pytest.raises(InvalidRecommendationInputError, match="来源证据"):
        evaluate_season([unsupported], region="华东", month=7)


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
