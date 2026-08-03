from app.services.texture_preference import convert_legacy_texture_preference
from app.services.texture_profile_report import (
    AUDIT_SINGLE_NEAR_TOP_THRESHOLD,
    COMPARISON_LABEL,
    COMPARISON_SCOPE,
    PROFILE_NAMES,
    V1_SOURCE_REVISION,
    _fruits,
    build_audit_report,
    build_report,
)


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
    assert tuple(first) == PROFILE_NAMES
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
    assert audit == {
        "comparison_label": COMPARISON_LABEL,
        "comparison_scope": COMPARISON_SCOPE,
        "profile_count": len(PROFILE_NAMES),
        "ordered_recommendation_change_count": changed_count,
        "ordered_recommendation_change_rate": round(
            changed_count / len(PROFILE_NAMES),
            6,
        ),
        "profiles": profiles,
    }
    assert audit["comparison_label"] == "固定合成画像对比"


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
        assert len(profile["v1_ranking"]) == eligible_count
        assert len(profile["v2_ranking"]) == eligible_count
        assert len(profile["v1_combination"]) == 2
        assert len(profile["v2_combination"]) == 2
        assert all(
            item["reasons"]
            for key in ("v1_combination", "v2_combination")
            for item in profile[key]
        )
