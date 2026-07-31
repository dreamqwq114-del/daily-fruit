# First-round independent audit: fruit identity and seed data

- Scope: `data/fruits_seed.json`, nutrition/season CSVs, seed loader and ORM
  fields.
- Method: read-only Pydantic validation, dry-run and SQL compilation; no
  Supabase write during the audit.

## Result

The dataset contains 24 unique fruit names and codes, one nutrition row per
fruit and 48 unique season natural keys. Roles are explicit (`main`,
`exploration`, `supporting`), identity codes are lowercase and aliases are
bounded. All demo values are marked low quality and carry the demonstration
scope note; they are not authoritative medical, nutrition or market data.

## Findings

- P0: none.
- P1 fixed: `Fruit.code` no longer has a constant unique default that could
  collide on a new ORM insert; legacy rows receive `legacy-<id>` in migration
  `0005`, while new seed rows always provide a code.
- P2 documented: the legacy season CSV has five columns. The loader explicitly
  derives `national`/`area`, availability 0.8/0.9 and `available` status for
  backward compatibility. A later curation task may author these three fields
  directly; the current values remain demonstration annotations.
- P2 documented: the demo seed has no `unavailable` rows; that branch is
  covered by algorithm fixtures instead of inventing market facts.

The seed path is idempotent by fruit name, nutrition fruit ID and season
natural key. Empty PostgreSQL alias arrays are emitted with an explicit
`VARCHAR(100)[]` cast.

