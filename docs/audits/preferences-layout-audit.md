# Preferences layout audit

Date: 2026-08-01
Auditor: independent read-only subagent (`/root/preferences_audit`)

## Scope

This audit covers the preference-page layout and copy change only. No backend,
database, recommendation algorithm, API contract, or field semantics were
changed in this task.

## Independent findings

| Check | Result |
| --- | --- |
| Discovery cards are inside `你的基本信息` | Pass |
| Horizon cards are inside `口感与食用偏好` | Pass |
| Old independent discovery and horizon fieldsets removed | Pass |
| One `discovery_level` and one `consumption_horizon_days` state path | Pass |
| Numeric values and API payload path unchanged | Pass |
| Defaults remain discovery `1` and horizon `4` | Pass |
| No duplicate form names/IDs; city remains absent from the UI | Pass |
| Radio-group semantics, visible selection, Tab/Enter/Space support | Pass |
| Recommendation algorithm and backend files unchanged | Pass |
| 375/768/1440 layout risk review | Pass by CSS review; live browser evidence limited below |

The subagent found one low-priority accessibility enhancement: the custom
radio groups do not implement optional Arrow-key movement from the full ARIA
Authoring Practices pattern. Each native button remains independently
Tab-focusable and supports Enter/Space, which meets this task's explicit
keyboard requirement; no blocking issue was found.

## Verification evidence

- Frontend tests: 23 Node unit tests and 29 component tests passed.
- Production build: `npm run build` passed after stopping the local preview
  process that had locked `frontend/dist` on Windows (`EPERM` was an environment
  lock, not a compile failure).
- GitHub Actions run `30685149610` completed the build and Pages deploy for
  commit `8efbf9e`; the public site returned HTTP 200 and its deployed
  JavaScript chunk contains the new `尝鲜偏好`、`食用时间` and
  `口感与食用偏好` labels.
- The layout uses two CSS grid columns on desktop/tablet, wide rows for name
  and discovery, and one-column grids below 680px. Horizon cards become a
  single column on small screens, avoiding text-driven horizontal overflow.

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
