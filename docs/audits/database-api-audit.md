# First-round independent audit: database, migration and API contract

- Scope: Alembic `0005`, SQLAlchemy metadata, repositories, application service
  and remote schema contract.
- Method: read-only local inspection and tests; remote project was only read
  before the reviewed migration.

## Baseline evidence

The only visible project was `Daily Fruit` (`frzbbpocyzlqxljsrsiw`,
`ap-northeast-1`). Before the write it was at `public.alembic_version=0004`
with 24/24/48 seed rows and 11/57/11/22/4 user and recommendation rows. All
business tables had RLS enabled and no browser policies.

## Findings and resolutions

- P0: none.
- P1 found and fixed: history, feedback and pair queries had no upper bound;
  repository methods now accept `until`, and the application passes the
  recommendation date/current UTC time.
- P1 found and fixed: nullable taste fields are included in migration `0005`
  with a safe downgrade guard.
- P1 found and fixed: downgrade protection runs before dropping V2 score
  columns and refuses to discard familiarity, nullable taste, or changed pair
  scores.
- RLS remains deny-by-default; no policies or grants were loosened.

## Remote result after implementation

Migration `0005` succeeded on the confirmed project. Read-only verification
reported version `0005`, the new columns/checks, RLS still enabled with zero
policies, and unchanged counts: fruits 24, nutritions 24, seasons 48, users
11, preferences 57, recommendations 11, items 22, feedback 4.

