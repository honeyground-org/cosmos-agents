## 0.4.1 — 2026-09-20

- Ship the reviewed interactive workspace and installation lifecycle improvements.
- Recheck current permissions and user decisions before retaining late results.
- Verified with isolated tests and real archive installation/removal/reinstallation. External publishing and purchases were not exercised.

# Changelog

## Unreleased

- Add agent-owned channel/reference and research layouts, saved per user without network or publishing access.
- Support integrated, independent app-window and external-browser placement on the matching development core/shell.
- Fix viewer imports after archive installation; verify settings and install/off/on/remove/reinstall with the actual loader and control plane.
- Preserve the original input draft across layout updates; add mobile detail/back navigation. 117 agent tests pass.

- Declare action-specific permissions for supporting Cosmos development cores.
  Search, details, summaries and trending no longer require publishing permission
  or publishing approval. The full manifest permission list remains unchanged.
- Saved views declare memory access, and reading setup no longer asks for an
  unnecessary upload connection.
- Run the isolated workspace preview through the real core dispatch with publishing
  denied. Add core dispatch and memory isolation regression coverage.
- Website interaction, background API access and a hybrid approach remain options
  for the final account-integration stage. Upload work is deferred until last.

Not released. Existing released cores retain agent-wide permission checks.

## 0.4.0 — 2026-09-08

- Dedicated channel/reference workspace on Cosmos 0.3.0+: search, selection,
  details, description-based summaries and browser actions with live state updates.
- User-scoped persistent results; search lists do not become inferred interests.
- Google connections refresh through the current Cosmos OAuth service.
- Opening requests are no longer falsely remembered as watched videos.
- Same-video lookups on the same day no longer inflate channel revisit counts.
- Credential-safe errors and trusted upload destinations with redirects disabled.
- Unavailable video metadata, memory failures and uncertain uploads are disclosed.
- Six workspace languages, responsive layout and reduced-motion support.

Known limits: actual Google account/YouTube publishing validation remains pending.
Summaries use title/description only. Permissions remain agent-wide. No automatic
upload retry or full YouTube channel synchronization is claimed.

### 2026-09-09 visual follow-up (unreleased)

- Preserve API-provided thumbnail URLs and prepare raster previews during actions.
- Render result thumbnails and the selected reference image under the unchanged CSP.
- Chart recorded uploads by date and visibility, without claiming live channel analytics.
- Use core palette tokens and add motion pause/reduced-motion support.
