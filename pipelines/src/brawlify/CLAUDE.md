# CLAUDE.md — brawlify

Pulls the BrawlAPI dump and builds the reference layer (brawlers, kits, texts, prices,
maps) the rest of brawl-stats joins against. Imported from the `brawlify-api` sandbox
(#39). The brawl-stats architecture it serves: `docs/ARCHITECTURE.md`.

## How to work here

- Write the code directly and run multi-step work straight through. No teaching mode.
- Comments: none for obvious behaviour. Document only obscure algorithms, complex logic,
  convoluted abstractions — and prefer a small helper that makes the comment unnecessary.
- Docstrings on public modules, classes and functions; module docstrings short.
- Long-form knowledge goes in `docs/brawlify/`, not in code. Update the relevant doc when
  a fact changes, without being asked.
- A refactor keeps `uv run pytest` green byte for byte. An intended output change is its
  own PR, with regenerated goldens (`pipelines/tests/brawlify/regenerate_golden.py`) and
  a reviewed diff.
- Stack: Python >=3.12, `uv`, `httpx`; dev: `ruff`, `pytest`.

## Map

- Code: `pipelines/src/brawlify/` — one CLI, `uv run brawlify <command>`
  (`docs/brawlify/commands.md`).
- Architecture, file layout and where to add things: `docs/brawlify/architecture.md`.
- Everything else: `docs/brawlify/README.md`.

## Token rules (non-negotiable)

- **Never a number in a recipe.** A recipe is a path; it self-corrects on the next dump.
- **`0` means unset** in this csv, never zero. Never emitted.
- **No default without proof.** Positional defaults cover MetaType 4 and 6 only.
  *A wrong number is invisible on the site, a missing one is not.*
- **A card listed in `RECIPES` is described entirely there.** A missing slot is deliberate.
- **Every recipe is checked in game**, the value recorded in
  `pipelines/inputs/brawlify/review/*.done`.
- `Unresolved` is the only caught exception. Real bugs must surface.
- `<VALUEn>` cannot be derived automatically (the client fills it from code). Do not
  retry ranking candidate paths automatically; hunt by value
  (`docs/brawlify/tokens/findings.md`).

## Before blaming a recipe

1. `uv run brawlify trace <DESC_TID> <token>`
2. hunt the value (x20 ticks, x1000 ms, x100 ammo, x40 ulti charge, /2 level)
3. check `metadata.generatedAt` and `docs/brawlify/tokens/balance-changes.md`: the dump
   lags the game

## Irreplaceable files

- `pipelines/inputs/brawlify/review/*.done` (in-game measurements) and
  `pipelines/inputs/brawlify/literals.json`: versioned, never regenerated.
- `data/raw/brawlify/history/`: archived dumps, exist nowhere upstream. Git-ignored;
  R2 backup is #78.
