# First-round independent audit: recommendation algorithm V2

- Scope: `backend/app/services/recommendation_service.py`, mapper, algorithm tests.
- Method: read-only review plus focused V2 tests; no Supabase write.
- Initial focused result: 42 passed.

## Findings

- P0: none.
- P1 found and fixed: mapper expressions such as `value or default` converted
  legitimate zero values into defaults. Mapping now uses an explicit `None`
  check, with regression coverage for zero availability, zero convenience
  attributes, and novelty level 0.
- P1 found and fixed: the four taste dimensions could not be unset and were
  always averaged as four 0.5-like values. The ORM/schema now allow null taste
  dimensions; the pure algorithm averages only configured dimensions and uses
  a neutral 0.5 prior only when none is configured.
- P2 retained as an explicit contract: `has_tried=NULL` means unknown, not
  tried and not forbidden. Explicit `False` is the only unfamiliar signal.
- P2 fixed during the same pass: feedback/history IDs, types, timezone and
  future dates are validated before scoring.

## Positive checks

Filtering covers inactive, forbidden, unwilling, supporting-role and explicitly
unavailable fruit. Nutrition normalization uses the complete active library,
portion grams, P05/P95 bounds, and preserves missing values. Pair selection
enumerates legal combinations, applies the 0.70/0.15/0.10/0.05 formula, and
uses a deterministic near-top random choice when seeded. Reasons carry the
actual weighted contribution.

