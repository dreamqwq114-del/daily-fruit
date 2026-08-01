# Preferences UI and persistence audit

Date: 2026-08-01
Auditor: independent read-only subagent (`/root/preferences_audit`)

## Evidence reviewed

- `frontend/src/components/ProfileFields.vue`
- `frontend/src/components/FruitPreferencePicker.vue`
- `frontend/src/utils/fruit-preferences.js`
- `backend/app/schemas/user.py`
- `backend/app/models/user.py`
- `backend/app/repositories/user_repository.py`
- `backend/app/services/user_service.py`
- `backend/alembic/versions/0006_user_consumption_horizon.py`
- backend and frontend tests, current Git status, and commit range
- Supabase read-only table, migration, security-advisor, and performance-advisor results

## Requirement results

| Area | Result |
| --- | --- |
| City removed from UI, old DB value preserved | Pass |
| Region seven areas plus stable unknown, no new 全国 option | Pass |
| Price labels 1/2/3 | Pass |
| Five taste/usage sliders and convenience semantics | Pass |
| Horizon 2/4/7, default 4, storage-only | Pass |
| Discovery cards 0/1/2, default 1 | Pass |
| Searchable 24-fruit picker with cancel/confirm | Pass |
| Favorite max five and conflict confirmation | Pass |
| Explicit-only preference payload, no neutral rows | Pass |
| Familiarity preservation and new favorite `has_tried=true` | Pass |
| Duplicate/missing fruit validation | Pass |
| Recommendation algorithm unchanged | Pass |
| Migration and remote schema verification | Pass |

## Database evidence

The confirmed target is Daily Fruit project ref `frzbbpocyzlqxljsrsiw`.
Migration 0006 added `users.consumption_horizon_days SMALLINT NOT NULL DEFAULT 4`
and the `(2, 4, 7)` check. Existing counts remained 12 users and 57
preference rows; all existing horizons are 4. RLS and existing policies were
not changed. The public schema still contains the nine expected business and
migration tables; no new table or data rewrite was made. Security advisors
reported the existing deny-by-default `RLS enabled without policies` posture
and the project's pre-existing disabled leaked-password protection. Performance
advisors reported three pre-existing unused indexes; none was removed in this
feature.

## Test evidence

- Backend: `180 passed, 28 skipped` (skips are isolated-database tests because
  `TEST_DATABASE_URL` is not configured in this workspace).
- Frontend: 23 unit tests and 29 component tests passed after the preference
  layout regression coverage was added.
- `npm run build` passed.
- GitHub Actions runs `30684180630`, `30684304591`, and `30685149610` passed
  both build and deploy jobs; `30685149610` contains the current frontend
  layout commit.

## Remaining verification boundary

The public site returned HTTP 200 and its latest deployed JavaScript/CSS
assets contain the new picker, horizon, and preference labels. The available
browser automation session retained a stale page and timed out while loading a
fresh deployment, so a live DOM/screenshot check at 375, 768, and 1440 CSS
pixels could not be completed in this environment. This is a verification
boundary, not a build or deployment failure; no production user or preference
data was changed solely for visual checking.

Legacy region values outside the seven displayed areas plus `UNKNOWN` are not
bulk-migrated. They are displayed as the stable unknown option by the current
frontend mapper and may be normalized only when the user saves the profile.
