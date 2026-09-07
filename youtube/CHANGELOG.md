# Changelog

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
