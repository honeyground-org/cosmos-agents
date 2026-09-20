# Flight finder

Keep the trip you are considering, compare the fares you have actually seen,
and pick a journey that fits your time as well as your budget.

> Development update, September 2026: the workspace below is **unreleased**.
> The dedicated view uses Cosmos 0.3.0's state/HTML contract. Independent action
> permissions require the newer, unreleased core action contract as well.

## What it does

Enter the origin, destination and dates, then add an airline or choose nonstop.
Return is optional. Swap airports with one button. Your saved trip fills the
form when you reopen the workspace; refreshing results does not erase a draft.

- A moving **route illustration** introduces the trip. It is a schematic,
  not a geographic map or a real aircraft position.
- Four selectable flight cards show the airline, listed local departure and
  arrival clocks, total travel time, stops and fare basis. Selecting a card or
  price bar updates the detailed itinerary beside it.
- **Fare bars** compare the current page, grouped by currency and fare basis,
  from zero. Unknown prices have no bar. Unknown stops are never called nonstop.
- **Observation history** shows the route minimum for the same trip and
  comparable currency/fare basis. It is not a forecast or the price history of
  one particular flight. A changed currency or fare basis starts a new history.
- **Compare nearby dates** reads the date grid as a separate action. Choose a
  returned date to search again while retaining the trip's return date. If
  grid labels cannot establish comparable conditions, no cheaper-day claim is
  made. In particular, airline/nonstop filters are not proven by these labels.
- **I booked it / Trip cancelled / Still deciding** save your decision and let
  you undo it. These buttons never buy a ticket.

The view uses the Cosmos palette and fonts, English originals and Korean,
Japanese, German, Spanish and French translations. It responds to selection,
loading and fare changes, pauses when hidden, and supports reduced motion and
an explicit pause button. The layout adapts to narrow screens.

## How it works

The brain stores a `wish` for the trip: origin, destination, departure and
return dates, airline/nonstop conditions, observed fare, currency, fare basis,
observation time and your booked/cancelled decision. A related `place` makes
the destination discoverable. Another date or different trip conditions form
a different trip, so unrelated fares do not overwrite one another.

A repeated search reads that trip before comparing fares. Repeating the current
route without new conditions continues its saved dates and conditions. Pass an
explicit empty value to clear a condition. Choices for this trip are **not**
stored as permanent preferences. Passenger names, passports, loyalty numbers,
booking references and payment details are not stored.

Detailed results belong to the current user's persistent workspace. State uses
the Cosmos storage provider in local and hosted deployments. Old contexts use
an account-specific file; an old file without an owner is not assigned to any
account automatically. Existing brain memories remain available; search again
to rebuild the screen.

When enabled and permitted, the background hook checks one eligible trip at a
time, no more often than roughly twelve hours per trip when Cosmos runs the
hook. This is not continuous monitoring or an airline fare alert subscription.
Booked, cancelled and departed trips are excluded. A worthwhile decrease can
raise a notice; increases stay on the screen.

## What it needs

The current implementation opens the Google Flights listing through Cosmos
`read_page`, then asks the configured model to extract only information on the
page. It does **not** use headline web-search snippets as a fare database. The
listing is opened in English for extraction; the workspace is localized.

| Action | Required permissions |
|---|---|
| Search | `memory`, `network`, `browser` |
| Compare nearby dates | `memory`, `network`, `browser`, `browser.act` |
| Saved view, pagination, decisions, tracking removal | `memory` |
| Open selected source | `memory` here; the delegated `browser_control` tool also enforces its permissions |

The full manifest declares all four capabilities. On older cores that do not
support action permissions, the full union still gates calls. Background hooks
also currently use the full union: denying browser clicking stops automatic
checks, although foreground search remains usable on the new contract. This
common hook limitation must be resolved before final permission validation.

The installed-agent **Currency** setting changes the requested listing currency;
`auto` uses the listing's choice. You can also expand **Search settings** in
the Flights view and save a currency, including **Listing default**. Both entry
points use the same standard setting, with no extra preference store. Changes
apply to the next search; existing cards and graphs keep their observed currency.
An unsaved selection survives refreshes; stale saves are rejected. Close and
reopen Search settings to load a change made elsewhere. The setting follows
Cosmos's deployment scope (one owner locally, user-specific in multiuser mode).
The **Tell you when something needs doing** toggle controls proactive checks.
Disabling it or the agent also suppresses late results from an ongoing check;
it does not cancel an already running provider request.

## Data and privacy

Data location depends on your Cosmos deployment. Trip conditions go to the
flight listing, and page content goes to your configured model. The iframe
makes no external requests; source URLs stay behind the action boundary.

## What it does NOT do

It does not book, pay, predict future fares, infer passenger identity or turn a
trip-specific airline choice into a lasting preference. It has no airline account.

## Limits

Fares are observations, not quotes. Check taxes, baggage, availability and the
arrival date at the source before booking. City-to-airport aliases, source
links, extracted times, dates and fare coverage still require real-service
verification. Explicitly conflicting destinations and departure dates are
rejected, rather than substituted as the requested trip.

Unknown fare basis is labeled as unconfirmed. Different currencies or known
fare bases never produce a single cheapest recommendation or a price-drop
claim. No currency conversion, guessed flight times or invented history is used.

Search errors retain previous results with an explanation. A successful empty
result clears the old list. Memory failures are visible. Stale screen actions
cannot open or change a newly searched trip. A source-open refusal remains a
refusal; it never means the flight was booked.

`tests/` and `scripts/check_workspace_ui.mjs` cover synthetic evidence using
real Cosmos state, memory, action dispatch, renderer and CSP. Start the isolated
preview with `scripts/preview_workspace.py --core /path/to/cosmos-billy`
(port 8805), then run the UI script with `FLIGHTS_PLAYWRIGHT_MODULE` pointing to
Playwright. `scripts/record_motion.mjs` records the actual workspace interaction.
The preview uses a temporary Cosmos home and never opens a real booking page.

The local-archive `scripts/check_installation.py` exercises the actual installer,
loader and control plane: install, settings from both entry points, off/on,
notice toggle, removal, restart discovery and reinstallation. Package removal
detaches the tool; personal settings and memories remain. This is not an
installer-button UI test or a published-version update test. The unit suite
currently passes 164 tests. The view loader works from an installed package,
without the source directory on the import path.

External accounts, web/API/hybrid selection, real listings and revocation are
collected for the final integration phase. No new release, user installation,
actual reservation or final real-use approval is claimed by these examples.

## Setup

Install the agent and open its Flights view or ask for a route in conversation.
Choose a currency in the agent settings if needed. Browser availability and
action permissions depend on the Cosmos deployment; account/service integration
remains a separate final validation step. No hand-entered API key is required.

## Support

Open an issue at <https://github.com/honeyground-org/cosmos-agents/issues>.
