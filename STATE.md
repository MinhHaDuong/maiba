# State

Last updated: 2026-04-28

## Current goal

**MVP that fixes ArchiveCCS as fast as possible.** Concretely: a single command
that reads `/home/haduong/CNRS/html/ArchiveCCS/ArchiveCCS.ris`, queries OpenAlex
and Crossref for the records with gaps, and writes back a corrected RIS — with
provenance lines so the changes are auditable.

Two design questions still need to be settled before code (`ARCHITECTURE.md` §2),
but the answers are constrained by "MVP, no overengineering."

## Status: SCAFFOLD ONLY

Project initialized 2026-04-28. Repository structure, conventions, ticket
system, Makefile, and `pyproject.toml` are in place. No `src/maiba/*.py` yet.

## Constraints (user, 2026-04-28)

- **Target collection:** `/home/haduong/CNRS/html/ArchiveCCS/ArchiveCCS.ris`
  (223 entries, ~24 DOIs, mixed JOUR / RPRT / NEWS / SLIDE / etc.).
- **No hardcoded constants** — anything tunable lives in a YAML config file.
- **Minimize state and cache** — every persistent file is a maintenance debt.
  Prefer pure functions and re-derivation over remembering. If a cache helps,
  it must be deletable without breaking correctness.
- **APIs:** OpenAlex and Crossref (see Climate Finance project patterns:
  `config/openalex_queries.yaml`, `scripts/catalog_openalex.py`, `utils.polite_get`).
- **LLM:** opt-in only, via OpenRouter (cloud) or padme local runtime. Default
  path is API-only and free.

## Open decisions (see ARCHITECTURE.md §2)

1. **UI shape** — recommendation: CLI only for MVP. Awaiting confirmation.
2. **Abstraction depth** — recommendation: Level 1 (two protocols, one impl each).
   Awaiting confirmation.
3. **State persistence** — recommendation: zero state for MVP. RIS in → RIS out.
   No database, no run log, no resume file. Each run is a pure function of the
   input file plus the current state of the web. Awaiting confirmation.
4. **Library backend for MVP** — RIS file roundtrip (not the Zotero SQLite).
   Reasoning: `ArchiveCCS.ris` already exists and is the unit of work; SQLite
   write-back means worrying about Zotero being open, schema versions, attachments.
   Defer SQLite until v1.

## Next actions (in order)

1. Confirm the four open decisions with the user (5-min conversation).
2. Open `tickets/0001-load-ris.erg` — read RIS, expose `Iterator[Item]`.
3. Open `tickets/0002-detect-gaps.erg` — classify each item by what's missing.
4. Open `tickets/0003-resolve-openalex.erg` — query OpenAlex for one item; merge.
5. Open `tickets/0004-resolve-crossref.erg` — same for Crossref; rank candidates.
6. Open `tickets/0005-write-ris.erg` — emit corrected RIS with provenance lines.
7. End-to-end smoke test: run on `ArchiveCCS.ris`, eyeball the diff.
8. Pick a license (MIT or Apache-2.0); commit `LICENSE`.

## Blockers

The four open decisions in `ARCHITECTURE.md` §2.

## Background

MAIBA was conceived 2026-04-28 while indexing the CCS PDF archive at
`/home/haduong/CNRS/html/ArchiveCCS/`. The exercise revealed that even a clean
RIS export had records with `AU - et al.`, missing dates, and missing DOIs that
regex couldn't fix. A janitor was needed; none existed in the form imagined.
