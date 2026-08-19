# Flight finder

Fare search is everywhere. **This one remembers.**

> *"That Tokyo route you were watching — it's 80,000 cheaper than when you looked."*

## What it does

You look at flights on a Monday. By Friday you have lost the number, so you
search again from scratch and have no idea whether 340,000 is a good price or a
bad one. Buying a ticket well takes weeks of that, and none of it survives.

This keeps the part that matters: **where you were trying to go, what day you
meant to leave, and what the fare was each time it looked.** So the second
search can tell you something the first one could not.

- **Four flights side by side on one screen** — price, how many times you change
  planes, how long the whole trip takes, and one sentence on why a flight is
  worth a look. Say *"show the next ones"* for the rest.
- **Say what you want and it looks for that.** Name an airline, ask for nonstop
  only, give a return date — the conditions go into the search *and* filter what
  comes back, and the screen shows which ones are on. When nothing matches it
  says **which condition is the problem** ("I found 5 flights, but none on
  Korean Air"), because "nothing found" makes people doubt the route instead of
  the filter they can actually drop.
- **It says what the price covers.** Each card marks a fare as one way or
  return when the results say so, and stays quiet when they do not. A round-trip
  search never recommends a one-way fare: 189,000 one way is not a better deal
  than 212,000 return, and putting them side by side implies it is.
- **The one it pushes is not simply the cheapest.** On a flight the cheapest is
  often the hardest — two stops and thirteen hours. It pushes the cheapest of
  the ones with the fewest stops, and the card says so in words. The cheapest
  overall is marked separately, so you can see the trade you would be making.
- **A trend, not a number.** Every search leaves an observation, so the screen
  can draw which way the fare is going. That is the thing you actually want to
  know before you book: is it worth waiting?
- **It tells you before you ask.** If a fare you are still thinking about drops,
  it says so at that moment rather than waiting for you to open a screen. Sales
  end; a price drop you hear about next week is not information.
- **It stops when it should.** The day you say you booked, and the day the plane
  leaves, it stops watching and takes its own notice down.

## How it works

It implements the Cosmos `plugin/v1` contract as a single file
(`flights_scout.py`) with its translations alongside (`flights_i18n.py`).

1. **Reads your memory first** — has this route been looked at before, and what
   did it cost then?
2. **Asks the web** through Cosmos's own `web_search` tool. The search terms go
   through translation, so a Korean or French user gets results in their own
   market rather than an English one.
3. **A model moves the results into rows** — airline, route, date, stops,
   duration, price, currency, link. That is *all* the model does. It is told
   never to invent a price or a date, and to leave unknown fields empty.
4. **Every judgement is our own code, and it is plain to read**: cheapest first,
   fewest stops as the tiebreak, unknown prices last, and the push is "cheapest
   of the ones with the fewest stops". Nothing is blended into a score — a score
   hides its reasons, and a ranking without reasons is indistinguishable from an
   advert.
5. **Writes the observation back** to the brain with the time it was taken, and
   draws the comparison on its own screen.

★The same route on a different day is a different trip.★ This is the one thing
flights need that shopping does not. September 10th to Tokyo and December 24th
to Tokyo are not the same thing, so the date is part of how the trip is
remembered. Without that, one peak-season search overwrites your off-season
memory and the next search reports a price rise that never happened.

## What it needs

| Permission | Why |
|---|---|
| `network` | To search the web for fares. It has no fare database of its own. |
| `memory` | ★This is the whole point.★ Without it every search is the first search, and "that route dropped" cannot be said at all. It stores the route, the destination and the fare it saw, with the time it saw it. |

Nothing else. It does not ask for the desktop, the screen, the clipboard or your
files.

## What it does NOT do

- **It does not book anything.** It has no payment permission and no airline
  account. The last button is always yours, on the airline's own site.
- **It never stores who is travelling.** No passenger names, no passport or
  frequent-flyer numbers, no booking references. The brain is searched and put
  into prompts; nothing that identifies a traveller belongs there.
- **It does not decide you booked.** Because it does not issue tickets, it
  cannot know. It asks, and it only records what you actually say — and you can
  take it back ("I have not booked it after all").
- **It does not turn your choices into a permanent "taste".** Picking a morning
  flight once is a judgement about that trip, not a preference of yours.
- **It does not tell you a fare went up.** You cannot act on that, so it stays
  on the screen where it belongs and never becomes an interruption.
- **It takes no commission and has no partner airlines.** Nothing in the ranking
  is paid for.

## Data and privacy

**Stays on your machine.** The routes, the destinations and the fares it
observed live in your Cosmos brain, on your own disk. So does the last
comparison it drew.

**Leaves your machine:** the search phrase only — the origin, the destination
and the date you asked about — sent to the web search Cosmos is already
configured to use, and the raw results sent to the model you configured, so it
can turn them into rows.

**Never leaves, and is never stored:** anything identifying a traveller.

You can see everything it kept by asking *"what routes have I been watching?"*,
and remove any of it with *"stop tracking that route"* or from the brain screen.

## Limits

- Fares come from **web search results, not from an airline API**. They can be
  stale or partial, and a fare can be gone by the time you click. Treat the
  screen as "worth a look", not as a quote.
- Travel time and stop counts are only as good as what the search results say.
  When the results do not say, the column reads *Unknown* rather than a guess.
- **Return dates go into the search, not into arithmetic.** It never doubles a
  one-way fare to guess a return price — it filters to fares the results
  actually describe as returns, and leaves the rest marked "unknown". When the
  results say nothing about what a price covers, neither does it.
- Fares in **different currencies are never compared.** If the same route comes
  back in USD when it was last seen in KRW, it says nothing rather than
  subtracting two numbers that do not mean the same thing.
- The background check looks at **one watched route at a time**, roughly twice a
  day, so a conversation never fans out into a dozen web searches.

## Setup

None. Install it and say *"find flights to Tokyo leaving on the 10th"*.

If you want it to stop speaking up on its own, turn off **"Tell you when
something needs doing"** on its card — the hook is declared, so turning it off
really does stop it being called.

## Support

Open an issue at
<https://github.com/honeyground-org/cosmos-agents/issues>.
