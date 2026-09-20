## 1.2.0 — 2026-09-20

- Ship the reviewed interactive workspace and installation lifecycle improvements.
- Recheck current permissions and user decisions before retaining late results.
- Verified with isolated tests and real archive installation/removal/reinstallation. External publishing and purchases were not exercised.

# Changelog

## Unreleased — AG-03

- Add a dedicated comparison workspace with account-scoped persistent state,
  remembered purchase criteria, candidate details, pagination and explicit outcomes.
- Split search permissions from saved-memory actions. Browser and Wallet retain
  their own permission checks. Requires the development core's action contract.
- Reject stale selections; confirm outcome writes and propagate browser refusal.
- Keep valid old results on search failure; clear them on an empty successful search.
- Compare one product in one currency instead of pooling unrelated prices;
  retain confirmed outcomes on subsequent searches.
- Isolate notice tracking and legacy migration marks by user; sanitize extraction
  signals and seller URLs; keep raw exception details out of user messages.
- Add isolated memory/state/permission tests and reproducible desktop/mobile UI captures.

### 2026-09-09 visual follow-up

- Display real source raster images through the new bounded core image contract;
  keep them in the account workspace and render under the unchanged iframe CSP.
- Add clickable zero-based price bars and a same-product two-observation graph.
- Add selected-image transitions, hover zoom and loading feedback with pause,
  reduced-motion and hidden-view handling; keep search drafts stable.
- Capture new desktop/mobile examples and an actual UI motion recording.

Real provider/login/Wallet integration remains deferred. No new
release tag or market-index entry is published by this development pass.

### 2026-09-09 installable-agent settings and lifecycle follow-up

- Add account-owned price-check settings in the comparison view: pause/resume,
  check interval and minimum percentage drop. Save without search permission.
- Preserve settings across searches, reject stale edits, and suppress late alerts
  after checks or the agent are disabled.
- Apply the 3,000 absolute-drop minimum only to KRW, not all currencies.
- Load the sibling viewer module during package attachment so an installed agent
  can open its view after the installer removes its temporary import path.
- Verify real archive install/loader/control-plane off/on/remove/reinstall in an
  isolated home; retain personal settings after reinstall. Add 11 behavior tests
  (121 total) and desktop/mobile settings screenshots with real canvas/CSP checks.
- No core execution changes, release or external service transactions in this pass.
