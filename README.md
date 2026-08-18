# Cosmos agents

First-party agents for [Cosmos](https://github.com/honeyground-org/cosmos-billy),
each in its own folder.

| Folder | Agent | What it is for |
|---|---|---|
| [`shopping/`](shopping/) | `honeyground-org/shopping` | Remembers what you were thinking of buying and tells you when the price moves |
| [`flights/`](flights/) | `honeyground-org/flights` | Remembers where you were trying to fly and tells you when that fare drops |

## Why one repository

Cosmos installs an agent from a repository plus a folder — the market index
entry carries `repo` **and** `path`. One repository per agent would mean one
release per agent, and work that takes many steps is work that quietly stops
happening.

**But the tags are per agent**, not per repository. One shared tag looked
simpler until there were two agents: fixing one would move the other's version
too, and a user would be told there is a new release of something that did not
change. So a release is `<folder>-vX.Y.Z` — `flights-v0.2.0`, `shopping-v1.1.1`
— and the index entry for an agent only moves when that agent moves.

## Layout

Each folder is a complete agent and nothing outside it is downloaded:

```
shopping/
├── cosmos-agent.yaml   the manifest Cosmos reads before installing
├── shopping_scout.py   the agent (entry: shopping_scout:ShoppingPlugin)
├── shopping_core.py    ranking, price comparison, what goes into memory
├── shopping_i18n.py    what it says, in five languages
├── README.md
└── tests/
```

**An agent carries its own translations.** While it lived inside Cosmos its
lines sat in the core catalogue and the core test suite checked that every
language had an answer. Out here that eye only sees core sources — so a new line
written here would go unchecked and quietly show up in English. Each agent ships
a `<name>_i18n.py` and a `tests/test_i18n.py` that checks it.

## Running the tests

The agents import Cosmos contracts, so the tests need a Cosmos checkout:

```bash
COSMOS_HOME=../cosmos-billy python -m pytest -q
```

`conftest.py` finds Cosmos through `COSMOS_HOME`, or as a sibling folder, and
**skips with a clear message** when it cannot — a green run that imported
nothing is worse than a red one.

## Publishing

A release is a git tag plus one line in
[`cosmos-market-index`](https://github.com/honeyground-org/cosmos-market-index):

```json
{"id": "honeyground-org/shopping",
 "repo": "https://github.com/honeyground-org/cosmos-agents",
 "path": "shopping",
 "ref": "shopping-v1.1.1"}
```

`ref` must be a tag or a commit SHA, never a branch: a branch is different code
tomorrow, and then nobody can say what a given install actually contains.

## Licence

MIT — see [LICENSE](LICENSE).
