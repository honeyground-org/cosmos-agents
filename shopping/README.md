# Shopping scout

Remember a buying decision across visits: what you considered, the observed price,
and the criteria for that purchase. Compare four candidates at a time and tell
Cosmos when you bought an item, dropped it, or are still considering it.

## Development status

AG-03 changes below are **unreleased**. Version 1.1.2 remains the published version.
The specialty workspace needs Cosmos 0.3.0's account state and HTML state contract.
Action-specific permissions additionally need the unreleased core action permission
contract. Older contexts retain declarative comparison blocks and whole-tool permissions.

## Using the workspace

Search for a product and optionally enter the criteria for this purchase. Leaving
criteria blank reuses the saved criteria for the same decision. To clear them,
tell Cosmos to search with `criteria: ""`. Criteria are stored on the `wish`, not
as permanent personal preferences. The new search uses the saved criteria again.

Select a candidate to inspect its reason, rating, review count, official-seller
signal and observation time. Unknown values remain unknown. Use Previous/Next to
compare the remaining candidates. Only displayed pages are recorded in the brain.
The price comparison pairs the first candidate with its earlier observation in the
same currency; it is not a market-wide historical price chart.

“I bought it”, “Stop considering” and “Still considering” record or undo the
selected candidate's outcome. These actions do not make a purchase. A stopped
candidate is removed from price watching; other candidates may remain watched.
A stale comparison button asks you to select again instead of changing its target.

“Visit seller” passes the saved HTTPS link through Cosmos' browser tool. It shows
the tool's result, including refusal. For checkout, ask Cosmos in conversation;
Shopping records checkout intent and hands off to Wallet. Wallet's permission
checks and the user's final purchase button remain separate.

## Permissions and settings

| Operation | Shopping permission | Additional handoff |
|---|---|---|
| Search | `network`, `memory`, `shopping.search` | Configured `web_search` tool |
| Saved comparison, pagination, purchase outcome, price-check settings | `memory` | None |
| Visit seller | `memory` | Browser tool's own permissions |
| Checkout request | `memory` | Wallet's own permissions and approval |

The manifest retains `requires: [wallet]` for checkout handoff. Comparison and settings
work without calling Wallet. Shopping has no account credentials to configure.

Open the Shopping view, then expand **Price check settings**:
turn background price checks on/off, choose 6/12/24/72 hours and a 7/10/15/20% drop.
Defaults are on, 12 hours and 7%. Saving settings never searches. Settings belong to
the current account and survive new or empty comparisons.

Checks require Cosmos, the agent and background suggestions to be enabled; the
interval is approximate, not a continuously running price feed. KRW also requires
at least a 3,000-won drop; other currencies use the selected percentage. The same
item is not alerted again within three days. Only the same item/currency is compared.
Pausing checks suppresses an alert from an already-running search when it returns;
it does not forcibly cancel that request.

Development validation uses the real package installer/loader/control plane in an
isolated home: install, off/on, remove, fresh registry and reinstall. Removal detaches
the tool and deletes its package; personal memory and component state remain and
settings are available after reinstall. This is not a published-update or actual
service-account test. Run `scripts/check_installation.py` with the core environment.

## Memory, data and limitations

- Buying intentions and explicit criteria live on Cosmos brain `wish` entities;
  observed candidates, reasons and purchase outcomes use `product` and `considering`.
- The latest comparison and pagination use Cosmos' account-scoped state store.
  Old ownerless `last_search.json` is not automatically assigned to a user. The
  brain remains available; repeat the search to create a new comparison.
- Storage follows the Cosmos deployment (local or hosted), not always this computer.
  Search terms and saved criteria go to the configured search provider. Search
  excerpts go to the configured model for extraction. Visiting a seller opens its site.
- Rating precedes price; prices are ordered only within the same currency. Commission
  is excluded. A model extracts fields from search evidence; live source accuracy
  and model hallucination resistance still require real-provider validation.
- The specialty workspace now shows source photographs, clickable price bars and
  a two-observation price graph. `prepare_agent_images` downloads bounded public
  HTTPS rasters during search and stores thumbnails in the current account workspace.
  Reopening the view makes no image requests. Missing/failed images show a clear fallback.
  This image contract is unreleased; older cores still show graphs with image fallback.
- Entry bars, selected photographs and loading feedback animate. Motion can be
  paused; reduced-motion settings and hidden-view lifecycle stop animation.
- Separate login-in-the-web, background API, or hybrid approaches are **not selected**.
  Real seller login, Wallet handoff and purchases have not been tested in this AG pass.
- Delete/reinstall, memory deletion versus cached views, same product across multiple
  buying decisions, currency decimals, and per-currency alert policy remain open.

## Validation

Run `shopping/tests` with `COSMOS_HOME` set to a temporary directory and
`COSMOS_LANG=en`. The visual follow-up has 110 passing tests, including actual Cosmos state,
brain recall, action permission dispatch, failure handling and user isolation.

`shopping/scripts/preview_workspace.py` starts an isolated renderer on port 8804.
It creates a temporary Cosmos home and uses synthetic search/model results; no
seller, real user account, browser or payment is contacted. Run
`shopping/scripts/check_workspace_ui.mjs` with `SHOPPING_PLAYWRIGHT_MODULE` pointing
to Playwright to validate actual Cosmos rendering/CSP, drafts, iframe preservation,
button round trips, errors and mobile layout, and save example screenshots.
