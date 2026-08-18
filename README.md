# Cosmos agents

First-party agents for [Cosmos](https://github.com/honeyground-org/cosmos-billy),
each in its own folder.

| Folder | Agent | What it is for |
|---|---|---|
| [`shopping/`](shopping/) | `honeyground-org/shopping` | Remembers what you were thinking of buying and tells you when the price moves |

## Why one repository

Cosmos installs an agent from a repository plus a folder — the market index
entry carries `repo` **and** `path`. One repository per agent would mean one
release per agent, and work that takes many steps is work that quietly stops
happening. Everything here ships together under one tag.

## Layout

Each folder is a complete agent and nothing outside it is downloaded:

```
shopping/
├── cosmos-agent.yaml   the manifest Cosmos reads before installing
├── shopping_scout.py   the agent (entry: shopping_scout:ShoppingPlugin)
├── shopping_core.py    ranking, price comparison, what goes into memory
├── README.md
└── tests/
```

## Running the tests

The agents import Cosmos contracts, so the tests need a Cosmos checkout:

```bash
COSMOS_HOME=../cosmos-billy python -m pytest shopping/tests -q
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
 "ref": "v1.0.0"}
```

`ref` must be a tag or a commit SHA, never a branch: a branch is different code
tomorrow, and then nobody can say what a given install actually contains.

## Licence

MIT — see [LICENSE](LICENSE).
