# Preferences settings implementation audit

Date: 2026-08-01

## Scope

This phase changes the onboarding and preferences UI and its persistence
contract. It does not change recommendation weights, season matching,
nutrition scoring, or convenience scoring.

## Implemented behavior

- The profile form collects username, region, price level, five taste/usage
  sliders, a 2/4/7-day consumption horizon, and discovery level 0/1/2.
- City is no longer collected by the Vue UI. `users.city` remains in the
  database and is preserved on partial updates; new API-created users default
  it to `UNKNOWN`.
- Region choices are the seven Chinese areas plus an internal `UNKNOWN` value
  displayed as `暂不确定`. The legacy `全国` value is not migrated.
- Fruit choices are grouped into especially loved, dislike, and forbidden.
  The picker is searchable, uses a confirm/cancel dialog, supports conflict
  confirmation, and limits especially loved fruits to five.
- The frontend submits only explicit managed states. It does not create
  neutral rows or submit familiarity fields.
- The backend maps a newly-created favorite to `has_tried=true`, preserves
  existing `has_tried` and `willing_to_try`, clears only managed fields for
  unselected rows, and never deletes preference rows.

## Database verification

- Target project: Daily Fruit, ref `frzbbpocyzlqxljsrsiw`.
- Before migration: Alembic `0005`, 12 users, 57 preference rows.
- Migration `0006_user_consumption_horizon` adds non-null
  `users.consumption_horizon_days` with default `4` and a `2,4,7` check.
- After migration: all 12 existing users have horizon `4`; no business rows
  were deleted or rewritten. `public.alembic_version` is `0006`.
- Existing RLS and deny-by-default policy posture was not changed.

## Risks and follow-up

- The city column remains for compatibility and should be removed only in a
  separately reviewed migration after all consumers stop relying on it.
- `consumption_horizon_days` is intentionally storage-only in this phase; it
  must not affect ranking until a separate algorithm design is approved.
- The unauthenticated browser path remains disabled; business API calls still
  require Supabase Auth and FastAPI JWT validation.
