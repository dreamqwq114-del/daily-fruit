# Market access data audit

Date: 2026-08-01
Scope: user purchase-condition collection and persistence

## Read-only baseline

- The settings form is `frontend/src/components/ProfileFields.vue` and is
  submitted by both `OnboardingView.vue` and `PreferencesView.vue`.
- Profile requests are `POST /api/me` for creation and `PUT /api/me` for
  updates. The frontend sends the profile object through the shared API
  client; it does not write business tables directly.
- `UserUpdate` already performs field-level partial updates. The service uses
  `model_dump(exclude_unset=True)`, so omitted fields are not overwritten.
- The current `public.users` ORM/table baseline contains `city`, `region`, the
  taste/price/convenience fields, `discovery_level`, and
  `consumption_horizon_days`. It does not yet contain the two requested
  purchase-condition columns.
- The target Supabase project was read-only checked before implementation:
  project ref `frzbbpocyzlqxljsrsiw`; `public.alembic_version` is at `0006`,
  `public.users` contains 14 rows, and the two requested columns are absent.
  Existing public business tables remain RLS-enabled. No data was changed by
  this audit.
- The repository migration baseline is `0006_user_consumption_horizon.py`.

## Planned minimal change

Add only these nullable-free user columns with safe defaults and checks:

- `market_access_level SMALLINT NOT NULL DEFAULT 2 CHECK (market_access_level BETWEEN 1 AND 3)`
- `accepts_online_purchase BOOLEAN NOT NULL DEFAULT false`

The migration will be additive and will not alter or delete `city`, fruit
tables, recommendation tables, seed data, or recommendation logic. Existing
rows receive the database defaults. The downgrade removes only these new
columns and the owned check constraint.

## Compatibility risks and controls

- Creation and read schemas will expose both fields with defaults, allowing
  old clients and old rows to be represented safely.
- Update schema fields remain optional and field-level; omitted fields retain
  their stored values. The frontend will submit the numeric/boolean values
  without replacing the whole profile object in the service.
- `market_access_level` accepts only 1, 2, or 3. `accepts_online_purchase`
  accepts a JSON boolean only.
- The recommendation service and all recommendation inputs remain unchanged;
  these fields are collected for future availability work and are not used in
  ranking, filtering, reasons, or feedback behavior.

## Expected files

- `frontend/src/components/ProfileFields.vue`
- `frontend/src/utils/fruit-preferences.js`
- `frontend/src/assets/base.css`
- `backend/app/models/user.py`
- `backend/app/schemas/user.py`
- `backend/alembic/versions/0007_user_market_access.py`
- focused frontend/backend tests and migration metadata tests

## Implementation verification

The implementation added the two fields in migration `0007`. The target
Supabase project was re-read after the migration: both columns exist on
`public.users` with the expected types, defaults, and market-access check.
All 14 existing users have `market_access_level = 2` and
`accepts_online_purchase = false`; no existing row has a null value for either
field. `public.alembic_version` is now `0007`, and the Supabase migration
history contains `add_user_market_access_fields`.

The remote migration was applied as additive DDL only. No user profile values,
fruit data, recommendation history, RLS, policies, or recommendation code were
changed. The Supabase security advisor still reports the project's existing
informational RLS-without-policy notices and the existing Auth leaked-password
warning; the performance notices are existing unused-index INFO findings and
are unrelated to these columns.

Local verification completed:

- Backend: 184 passed, 29 skipped (database integration tests are skipped when
  the isolated `daily_fruit_test` URL is not configured).
- Frontend: 23 unit tests and 29 component tests passed; `npm ci` and
  `npm run build` passed.
- GitHub Pages run `30687904936` succeeded for commit `1073ba4`; the public
  site returned HTTP 200 and its deployed preference chunk contains both new
  field bindings.

## Independent read-only audit

The independent subagent review returned **PASS** and did not modify files.

- The ORM, schemas, API service, and migration agree on the two fields and
  their defaults (`2` and `false`).
- `UserUpdate` remains field-level (`exclude_unset=True`); omitted purchase
  fields and `city` are retained.
- Migration `0007` is additive and its downgrade owns only the two columns and
  the market-access check constraint. It does not write data or touch other
  schemas.
- The frontend has one select for `market_access_level` (1/2/3) and one boolean
  checkbox for `accepts_online_purchase`; there are no duplicate field names.
- The recommendation service, fruit data, and existing algorithm inputs were
  not changed. The responsive grid has a mobile single-column fallback with no
  identified fixed-width overflow risk.
- Targeted backend and frontend tests passed. The independent reviewer noted
  that its targeted frontend command was narrower than the full suite; the
  main verification above is the authoritative full-suite result.
- No tracked `.env` or real secret was found. Example credentials in tests are
  placeholders only.

Authenticated live-browser screenshots at 375/768/1440px were not completed
because no authenticated browser session was available. Static production
checks were completed instead: GitHub Pages returned HTTP 200, and the
deployed preference chunk contains both field bindings.

The implementation is ready for the next stage. These fields remain collected
for future availability features and are intentionally not used by the current
recommendation ranking, filtering, reasons, or feedback logic.
