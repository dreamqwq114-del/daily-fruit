# Preferences control audit

Date: 2026-08-01
Auditor: independent read-only subagent (`/root/preferences_audit`)

## Results

| Check | Result |
| --- | --- |
| Discovery is a native select like price preference | Pass |
| Discovery values remain 0/1/2 with default 1 | Pass |
| Horizon is a three-segment control | Pass |
| Horizon values remain exactly 2/4/7 with default 4 | Pass |
| Existing profile state and API payload are reused | Pass |
| Existing data can be echoed without API changes | Pass |
| No duplicate name/id or duplicate state | Pass |
| Backend, database, and recommendation algorithm unchanged | Pass |
| Tab/Enter/Space and visible selected state | Pass |
| 375/768/1440 responsive layout review | Pass by CSS review |

The audit confirmed that the horizon buttons only assign
`model.consumption_horizon_days`; they do not introduce a second state. The
onboarding save path still sends the same `{ ...profile }` payload, and the
preference page uses the same model path.

## Non-blocking accessibility notes

The custom horizon radio group does not implement optional Arrow-key movement
and roving tabindex from the complete ARIA Authoring Practices pattern. Each
native button is independently reachable with Tab and supports Enter/Space,
which satisfies the requested keyboard behavior. At widths below 680px the
three segments stack vertically to avoid text-driven horizontal overflow; this
is intentional responsive behavior.

## Verification

- `npm ci`: passed.
- `npm test`: 23 unit tests and 29 component tests passed.
- `npm run build`: passed.
- No backend, database, API, or algorithm files changed.

The existing component suite exercises onboarding payload submission; there is
no dedicated `PreferencesView` test for the PUT path. Static review confirms
that it shares the same `ProfileFields` model and `{ ...profile }` update path,
so this is a coverage boundary rather than a detected behavior change.

## Browser boundary

The authenticated preference route was not available for a complete live DOM
check in this environment: the local preview has no public authentication
configuration and redirects to login, while the existing external browser tab
has a stale session and refreshes time out. No user data was submitted. The
final deployment check will verify the public HTTP response and deployed asset
labels; the authenticated 375px/768px/1440px visual check remains a manual
follow-up if the browser session becomes available.
