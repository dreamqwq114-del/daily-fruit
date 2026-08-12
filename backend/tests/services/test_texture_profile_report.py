from pathlib import Path

from app.services.texture_baseline_replay import verify_checked_in_baseline
from app.services.texture_preference import convert_legacy_texture_preference
from app.services.texture_profile_report import (
    AUDIT_SINGLE_NEAR_TOP_THRESHOLD,
    COMPARISON_LABEL,
    COMPARISON_MONTH,
    COMPARISON_SCOPE,
    COMPARISON_TODAY,
    PROFILE_NAMES,
    V1_SOURCE_REVISION,
    _fruits,
    build_audit_report,
    build_report,
)


EXPECTED_PROFILE_NAMES = (
    "biased_sweet_crisp",
    "sweet_soft",
    "sour_crisp",
    "sour_soft",
    "high_sweet_sour",
    "sweet_only",
    "texture_only",
    "sour_only",
    "no_sensory",
    "migrated_consistent",
    "migrated_conflict",
    "low_budget",
    "high_convenience",
    "explicit_dislike_mango",
    "forbidden_mango",
    "refuses_untried_durian",
    "unavailable_mango",
    "recent_repeat_mango",
    "negative_feedback_mango",
)
EXPECTED_ACCEPTANCE_CHECKS = {
    "explicit_dislike_mango_hard_exclusion",
    "forbidden_mango_hard_exclusion",
    "refuses_untried_durian_hard_exclusion",
    "unavailable_mango_hard_exclusion",
    "recent_repeat_mango_lowers_score",
    "negative_feedback_mango_lowers_score",
    "low_budget_lowers_durian_score",
    "high_convenience_lowers_pineapple_score",
}
ROOT = Path(__file__).resolve().parents[3]


def test_legacy_texture_conversion_preserves_unknown_and_conflict_semantics() -> None:
    assert convert_legacy_texture_preference(None, None) == (None, "unset")
    assert convert_legacy_texture_preference(None, 0.8) == (0.8, "migrated_from_crisp")
    assert convert_legacy_texture_preference(0.2, None) == (0.8, "migrated_from_soft")
    value, source = convert_legacy_texture_preference(0.2, 0.8)
    assert value == 0.8 and source == "migrated_consistent"
    assert convert_legacy_texture_preference(0.1, 0.1) == (None, "legacy_conflict")


def test_fixed_texture_profiles_are_deterministic_and_report_near_top_without_re_tuning() -> None:
    first = build_report()
    second = build_report()
    assert first == second
    assert PROFILE_NAMES == EXPECTED_PROFILE_NAMES
    assert tuple(first) == EXPECTED_PROFILE_NAMES
    assert all(
        {
            "v1_taste_similarity_mean",
            "v1_taste_similarity_std",
            "v1_rank1_rank2_gap",
            "v1_single_near_top_count",
            "v1_pair_near_top_count",
            "v1_final_top2",
            "v1_reason_count",
            "v2_taste_similarity_mean",
            "v2_taste_similarity_std",
            "v2_rank1_rank2_gap",
            "v2_single_near_top_count",
            "v2_pair_near_top_count",
            "v2_final_top2",
            "recommendation_changed",
            "v2_reason_count",
            "comparison_scope",
            "audit_single_near_top_threshold",
            "production_pair_near_top_threshold",
        } <= set(report)
        for report in first.values()
    )
    assert any(report["recommendation_changed"] for report in first.values())
    assert first["migrated_conflict"]["v2_taste_similarity_mean"] == 0.5
    assert all(
        report["comparison_scope"] == COMPARISON_SCOPE
        and report["audit_single_near_top_threshold"]
        == AUDIT_SINGLE_NEAR_TOP_THRESHOLD
        for report in first.values()
    )


def test_order_only_changes_are_counted_as_recommendation_changes() -> None:
    report = build_report()
    assert all(
        item["recommendation_changed"]
        == (item["v1_final_top2"] != item["v2_final_top2"])
        for item in report.values()
    )


def test_audit_summary_reports_order_sensitive_synthetic_profile_change_rate() -> None:
    audit = build_audit_report()
    profiles = audit["profiles"]
    changed_count = sum(
        item["v1_final_top2"] != item["v2_final_top2"]
        for item in profiles.values()
    )
    assert audit["comparison_label"] == COMPARISON_LABEL
    assert audit["comparison_scope"] == COMPARISON_SCOPE
    assert audit["profile_count"] == 19
    assert audit["ordered_recommendation_change_count"] == changed_count
    assert audit["ordered_recommendation_change_rate"] == round(
        changed_count / len(PROFILE_NAMES),
        6,
    )
    assert audit["comparison_context"]["today"] == COMPARISON_TODAY.isoformat()
    assert audit["comparison_context"]["month"] == COMPARISON_MONTH
    assert audit["profiles"] == profiles
    assert set(audit["acceptance_checks"]) == EXPECTED_ACCEPTANCE_CHECKS
    assert all(audit["acceptance_checks"].values())
    assert audit["formula"]["production_pair_near_top_threshold"] == 0.03
    assert audit["v1_distribution"]["candidate_count_min"] >= 2
    assert audit["v2_distribution"]["candidate_count_min"] >= 2
    assert audit["v2_distribution"]["largest_ordered_pair_share"] == round(
        16 / 19,
        6,
    )
    assert audit["business_quality_decision"].startswith("requires_review")

    documentation = (
        ROOT / "docs/recommendation-texture-audit.md"
    ).read_text(encoding="utf-8")
    expected_markers = {
        f"ordered_recommendation_change_count={changed_count}",
        "ordered_recommendation_change_rate="
        f"{audit['ordered_recommendation_change_rate']:.6f}",
        f"v2_unique_top1_count={audit['v2_distribution']['unique_top1_count']}",
        "v2_unique_ordered_pair_count="
        f"{audit['v2_distribution']['unique_ordered_pair_count']}",
        "v2_largest_ordered_pair_share="
        f"{audit['v2_distribution']['largest_ordered_pair_share']:.6f}",
    }
    assert all(marker in documentation for marker in expected_markers)


def test_report_uses_complete_seed_context_and_auditable_v1_evidence() -> None:
    fruits = _fruits()
    assert len(fruits) == 24
    assert all(fruit.nutrition is not None for fruit in fruits)
    assert all(fruit.seasons for fruit in fruits)
    assert len(V1_SOURCE_REVISION) == 40
    eligible_count = sum(
        fruit.daily_recommendation_role == "main" for fruit in fruits
    )

    report = build_report()
    for profile in report.values():
        assert len(profile["v1_ranking"]) == profile["v1_candidate_count"]
        assert len(profile["v2_ranking"]) == profile["v2_candidate_count"]
        assert eligible_count - 1 <= profile["v1_candidate_count"] <= eligible_count
        assert eligible_count - 1 <= profile["v2_candidate_count"] <= eligible_count
        assert len(profile["v1_combination"]) == 2
        assert len(profile["v2_combination"]) == 2
        assert all(
            item["reasons"]
            for key in ("v1_combination", "v2_combination")
            for item in profile[key]
        )


def test_checked_in_v1_baseline_matches_fresh_source_revision_replay() -> None:
    verify_checked_in_baseline()
