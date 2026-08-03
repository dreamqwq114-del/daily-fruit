"""Texture preference migration and model-version constants."""

from __future__ import annotations

from math import isfinite


SCORING_MODEL_VERSION = "taste-v2"
FRUIT_PROFILE_VERSION = "2026-08-texture-v1"
TEXTURE_PREFERENCE_SOURCES = frozenset(
    {
        "explicit_new",
        "migrated_consistent",
        "migrated_from_soft",
        "migrated_from_crisp",
        "legacy_fallback",
        "legacy_conflict",
        "unset",
    }
)
LEGACY_TEXTURE_SYNC_SOURCE = "derived_from_texture"
LEGACY_CONSISTENCY_TOLERANCE = 0.20


def convert_legacy_texture_preference(
    soft_preference: float | None,
    crisp_preference: float | None,
) -> tuple[float | None, str]:
    """Convert legacy soft/crisp fields without turning conflicts into 0.5."""

    if soft_preference is not None and crisp_preference is not None:
        converted_from_soft = 1.0 - float(soft_preference)
        if abs(float(crisp_preference) - converted_from_soft) <= LEGACY_CONSISTENCY_TOLERANCE:
            return (float(crisp_preference) + converted_from_soft) / 2.0, "migrated_consistent"
        return None, "legacy_conflict"
    if crisp_preference is not None:
        return float(crisp_preference), "migrated_from_crisp"
    if soft_preference is not None:
        return 1.0 - float(soft_preference), "migrated_from_soft"
    return None, "unset"


def validate_texture_value(value: float | None) -> float | None:
    if value is None:
        return None
    if not isfinite(float(value)) or not 0 <= float(value) <= 1:
        raise ValueError("texture preference must be between 0 and 1")
    return float(value)


__all__ = [
    "FRUIT_PROFILE_VERSION",
    "LEGACY_TEXTURE_SYNC_SOURCE",
    "SCORING_MODEL_VERSION",
    "TEXTURE_PREFERENCE_SOURCES",
    "convert_legacy_texture_preference",
    "validate_texture_value",
]
