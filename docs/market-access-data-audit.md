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

No migration or remote database write has been performed at the time of this
baseline document.
