# Preferences control audit

Date: 2026-08-01
Auditor: independent read-only subagent (`/root/control_slider_audit`)

## Results

| Check | Result |
| --- | --- |
| Discovery is a native select like price preference | Pass |
| Discovery values remain 0/1/2 with default 1 | Pass |
| Horizon is a three-stop range slider | Pass |
| Horizon values remain exactly 2/4/7 with default 4 | Pass |
| Existing profile state and API payload are reused | Pass |
| Existing data can be echoed without API changes | Pass |
| No duplicate name/id or duplicate state | Pass |
| Backend, database, and recommendation algorithm unchanged | Pass |
| Tab/Enter/Space and visible selected state | Pass |
| 375/768/1440 responsive layout review | Pass by CSS review |

The audit confirmed that the horizon range slider derives an index from the
existing `consumption_horizon_days` field and maps its three positions to
`2/4/7`; it does not introduce a second state. The onboarding save path still
sends the same `{ ...profile }` payload, and the preference page uses the same
model path.

## Non-blocking accessibility notes

The native horizon range input supports Tab, Arrow-key, Home/End, and direct
keyboard adjustment. Its output label and end hints make the three valid
positions visible. At widths below 680px the slider remains full-width and the
labels wrap safely without horizontal overflow.

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
public GitHub Pages deployment nevertheless returned HTTP 200, and the latest
deployed JavaScript chunk contains the new horizon control and preference
field bindings. The authenticated 375px/768px/1440px visual check remains a
manual follow-up if the browser session becomes available.

Deployment evidence for this slider revision will be recorded after the
GitHub Pages workflow completes. The previous successful run predates this
native range-slider change and is not treated as evidence for the current
revision.
