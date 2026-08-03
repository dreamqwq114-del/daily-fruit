# First-round independent audit: recommendation algorithm V2

- Scope: `backend/app/services/recommendation_service.py` Facade,
  `backend/app/services/recommendation_core/`, mapper, and algorithm tests.
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
unavailable fruit. Nutrition normalization uses the complete active library's
0–1 unitless demo indices, P05/P95 bounds, and preserves missing values;
`default_portion_grams` is not used in this calculation. Pair selection
enumerates legal combinations, applies the 0.70/0.15/0.10/0.05 formula, and
uses a deterministic near-top random choice when seeded. Reasons carry the
actual weighted contribution.

## Fruit semantic correction audit

- `display_group` is a presentation and directory grouping field. It is not
  read by the pure recommendation core, so changing a group's label cannot
  change a base score, pair score, or ranking.
- The public field name `sensory_category_diversity` is retained for API
  compatibility, but its implementation is Scheme A: the average absolute
  difference across sweet, sour, soft, and crisp scores only. It does not read
  `category` or `display_group`.
- Static `daily_recommendation_role=exploration` is no longer valid. Exploration
  is derived per user from explicit familiarity and willingness fields; the
  compatibility cold-start constant is zero and contributes no score.
- `novelty_level` remains explanatory metadata and does not directly affect
  ranking. Supporting fruit is excluded from ordinary two-main-fruit output by
  the default selection path.
- `commonness_score` is a demonstration estimate for ordinary supermarkets and
  mainstream e-commerce in mainland China; it is distinct from `novelty_level`
  and is not treated as a universal botanical property.

The season loader still has an audit item: an out-of-window row can have
`season_score=0` while retaining its demonstration `availability_score`. This
is recorded for a separate data-semantics task and is intentionally unchanged
here. Soft/crisp remain four independent, equally weighted taste dimensions;
their observed correlation is not sufficient evidence to change the API or
formula in this task. Supabase RLS and the existing security-advisor warning
were observed but not modified.
