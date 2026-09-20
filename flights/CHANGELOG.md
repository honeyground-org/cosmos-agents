## 0.5.0 — 2026-09-20

- Ship the reviewed interactive workspace and installation lifecycle improvements.
- Recheck current permissions and user decisions before retaining late results.
- Verified with isolated tests and real archive installation/removal/reinstallation. External publishing and purchases were not exercised.

# Changes

## Unreleased — installable-agent follow-up

- Fix the installed package failing to open its HTML view because the viewer
  module was imported after the installer removed its temporary import path.
- Add collapsible search currency controls using the existing standard setting;
  retain original fare currencies and apply changes only to future searches.
- Use a valid `auto` option so users can restore the listing default. Reject
  invalid/stale saves and preserve unsaved selections through view refreshes.
- Recheck agent/notice enablement after a provider response to suppress late
  alerts when a user turns either off during a check.
- Validate 164 tests, actual local-archive install/off/on/remove/reinstall, and
  desktop/mobile UI with synthetic data. Published updates and real use remain pending.

## Earlier unreleased work — AG-04

- Dedicated flight workspace: editable trip form, route illustration, selected
  itinerary, interactive fare bars, observed history and nearby-date actions.
- Keyboard-accessible controls, responsive layout, five translations, reduced
  motion and pause/hidden lifecycle handling.
- Per-user persistent state and notice tracking; saved trip conditions and
  booking decisions survive reopening and repeat searches.
- Search, date-grid clicking and memory-only actions use separate capabilities
  on the unreleased core contract. Source opening delegates to browser_control.
- Stop comparing different currencies/fare bases; reject explicit conflicting
  routes/dates; unknown stop counts no longer become nonstop.
- Preserve old results on errors, clear them on empty results, report memory
  failure and reject stale screen actions.
- Synthetic tests and reproducible screenshots/video. Real-service integration,
  published update and final user validation remain pending.
