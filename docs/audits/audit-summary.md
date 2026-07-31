# V2 first-round audit summary

Four independent read-only audits were completed before the remote write:

1. algorithm and scoring;
2. database, migration and API;
3. fruit data and seed;
4. test, edge-case and exposure review.

No P0 issue was found. The P1 issues were fixed before migration: zero-value
mapping, unset taste dimensions, future event bounds, safe downgrade ordering,
the favorite/untried contradiction, and the seven-profile comparison gap.

The only intentional P2 remains the legacy season CSV compatibility rule. It is
documented and does not claim authoritative market availability. The remote
target was re-confirmed before migration; no auth, storage, RLS policy or
browser grant was changed.

Second-round result: two independent read-only audits rechecked the repaired
working tree and remote `0005` schema. One ORM default mismatch was found and
fixed by removing three model-side defaults that do not exist in PostgreSQL.
The fixed-profile executable regression now covers all seven report rows.
There are no remaining P0/P1 findings. Remaining P2 notices are the expected
deny-by-default RLS advisor messages and the separate Supabase Auth leaked
password-protection setting; neither was changed in this backend-only task.
