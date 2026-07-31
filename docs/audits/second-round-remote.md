# Second-round independent remote audit

The target was re-confirmed as `Daily Fruit` / `frzbbpocyzlqxljsrsiw` and was
checked read-only after migration and the two seed runs.

- `public.alembic_version=0005` and migration `recommendation_v2_data_model`
  is present;
- V2 columns, CHECK constraints, unique constraints and foreign-key delete
  rules match the local migration;
- rows remain 24 fruits, 24 nutritions, 48 seasons, 11 users, 57 preferences,
  11 recommendations, 22 items and 4 feedback records;
- codes, required V2 fields and recommendation scores have no null/duplicate
  quality failures;
- all business tables and `alembic_version` retain RLS with zero policies.

One P1 mismatch was found: the ORM declared server defaults for the three new
recommendation score columns while PostgreSQL has no defaults. The three model
defaults were removed; the service already writes explicit values. P0/P1
remaining: none. Supabase Auth leaked-password protection and deny-by-default
RLS advisor notices remain P2/intentional scope items.

