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
not changed.

## Test evidence

- Backend: `180 passed, 28 skipped` (skips are isolated-database tests because
  `TEST_DATABASE_URL` is not configured in this workspace).
- Frontend: 23 unit tests and 25 component tests passed.
- `npm run build` passed.
- GitHub Actions run `30684180630` passed both build and deploy jobs.

## Remaining verification boundary

The implementation is ready for the final responsive browser check at 375,
768, and 1440 CSS pixels. No production user or preference data should be
changed solely for this visual check.
