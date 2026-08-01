# Preferences layout audit

Date: 2026-08-01
Auditor: independent read-only subagent (`/root/control_slider_audit`)

## Scope

This audit covers the preference-page layout and copy change only. No backend,
database, recommendation algorithm, API contract, or field semantics were
changed in this task.

## Independent findings

| Check | Result |
| --- | --- |
| Discovery control is inside `你的基本信息` | Pass |
| Horizon slider is inside `口感与食用偏好` | Pass |
| Old independent discovery and horizon fieldsets removed | Pass |
| One `discovery_level` and one `consumption_horizon_days` state path | Pass |
| Numeric values and API payload path unchanged | Pass |
| Defaults remain discovery `1` and horizon `4` | Pass |
| No duplicate form names/IDs; city remains absent from the UI | Pass |
| Select/range semantics, visible selection, keyboard support | Pass |
| Recommendation algorithm and backend files unchanged | Pass |
| 375/768/1440 layout risk review | Pass by CSS review; live browser evidence limited below |

The later control pass replaced the custom choice groups with a native
discovery select and a native three-stop horizon range input. This removes the
previous custom-radio Arrow-key limitation while preserving the same field
values and save path.

## Verification evidence

- Frontend tests: 23 Node unit tests and 29 component tests passed.
- Production build: `npm run build` passed after stopping the local preview
  process that had locked `frontend/dist` on Windows (`EPERM` was an environment
  lock, not a compile failure).
- GitHub Actions run `30685834387` completed the build and Pages deploy for
  commit `e8c3d24`; the public site returned HTTP 200 and its deployed
  preference chunk contains a native `type="range"` input bound to
  `consumption_horizon_days`, with no legacy `horizon-segmented` control.
- The layout uses two CSS grid columns on desktop/tablet, wide rows for name
  and discovery, and one-column grids below 680px. The horizon slider stays
  full-width on small screens, avoiding text-driven horizontal overflow.

## Browser boundary

The requested real-browser check was attempted against the local production
preview and the deployed GitHub Pages tab. The local preview correctly opened,
but authentication was not configured in the local public build, so the route
redirected to the login page before the protected preference form rendered.
The existing external GitHub Pages tab retained a stale session/page and timed
out when refreshed by the browser connector. Therefore no claim is made that
375px, 768px, and 1440px were visually verified in a live authenticated DOM.
No user data was submitted or changed during these checks.

## Conclusion

The requested structural change is ready to ship. The only remaining manual
check is to open the authenticated site, hard-refresh it, and inspect the
preference page at 375px, 768px, and 1440px; this does not require any backend
or database change.
