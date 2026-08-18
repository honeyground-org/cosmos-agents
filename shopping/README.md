# Shopping scout

Shopping search is everywhere. This one **remembers**.

## What it does

You mention you are thinking about buying something. Days pass. When you come
back to it, Cosmos already knows where you left off:

> *"The Sony WF-1000XM5 you were looking at is 12,000 cheaper than last time."*

Four candidates stand side by side on **one screen** — photo, price, how many
people reviewed it, and whether the seller is an official store. The one it
pushes says **why** in a sentence, and if a cheaper one exists further down the
list it is labelled there, not here. Say *"show the next ones"* for the next
four.

When you decide, it can hand the purchase to Wallet. **The last button is
yours** — this agent never completes a payment.

Say it out loud:

- *"I am thinking about buying a standing desk"*
- *"Did anything I was watching get cheaper?"*
- *"Show the next ones"*

## How it works

It implements the Cosmos `plugin/v1` contract; the entry point is
`shopping_scout:ShoppingPlugin`.

1. **Reads memory first** — what did you look at last time, and at what price
2. **Searches the web** through Cosmos' `web_search` tool, then a model turns
   the raw results into candidates. The model only *transcribes*; it never
   ranks. Ranking that changes every time is ranking nobody can explain
3. **Writes to Cosmos' memory**, not to a private store of its own — otherwise
   nothing else in Cosmos could answer *"what was I about to buy?"*
4. **Compares with last time** and says what moved

Ranking uses price and rating only. **Commission never lifts anything**, and
where a link pays us is printed on that row — a footnote nobody reads is not a
disclosure.

The screen is drawn from Cosmos' declared view blocks (`compare`,
`price_history`), so it follows your theme and works the same in the desktop app
and the browser.

## What it needs

| Permission | Why |
|---|---|
| `network` | to search shops. Without it there is nothing to compare |
| `memory` | ★this is the whole point★ — the price you saw on Tuesday has to survive until Friday, and it has to live in Cosmos' memory so other parts of Cosmos can use it |
| `shopping.search` | marks this agent as one that looks at what you buy, so the install screen can say so plainly |

It also declares `requires: [wallet]`. Comparison works without Wallet, but
*"help me buy this"* would do nothing — and a button that silently does nothing
is worse than no button.

## What it does NOT do

- **It does not buy anything.** It hands the purchase to Wallet, which asks you
  to approve; you press the final button on the shop's own page
- **It does not see your card.** Card details live in Wallet's vault and never
  pass through here
- **It does not turn your choices into a permanent profile.** What you weighed
  while picking one thing — price, delivery, seller reputation, a colour — stays
  attached to *that* decision and goes when it goes. It never becomes "you like
  cheap things"
- **It does not rank by commission**, and it does not hide that a link pays us
- **It does not invent numbers.** A price, rating or review count it could not
  read is shown as "unknown", never as a plausible-looking figure
- **It does not talk to you on its own.** It answers when asked

## Data and privacy

Stays on your machine, in Cosmos' memory:

- **what you are thinking of buying** (`wish`) — your own words
- **the candidates and their prices** (`product`), with the time each price was
  read, so an old price is never shown as today's
- **that you went to checkout** — recorded as *"went to checkout"*, never as
  *"bought"*. We do not run the payment, so we cannot know. Next time it
  **asks** you

Leaves your machine:

- **your search terms**, to the web search Cosmos is configured to use
- **nothing else.** No account, no history upload, no analytics

Product photos are loaded from the shop's own image address, so that shop sees
your IP the same way it would if you opened the page. Delete anything of this at
any time from Cosmos' memory screen.

## Limits

- Prices are what the search results said **at the time they were read**. Shops
  change them constantly; the timestamp on each card is there for that reason
- Coupons, card discounts and shipping are usually not in the listed price
- Comparison quality depends on the search results. Small local shops often do
  not appear at all
- It keeps twelve candidates per search. If none of them fit, search again with
  different words rather than paging forever

## Setup

None. Install it and talk.

Wallet is worth installing alongside if you want *"help me buy this"* to work.

## Support

Issues: <https://github.com/honeyground-org/cosmos-agents/issues>

## Licence

MIT.
