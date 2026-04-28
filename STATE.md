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

## Decisions locked (2026-04-28)

All four open decisions confirmed by user. See `ARCHITECTURE.md` §8 for the log.

- UI: pure CLI for MVP
- Abstraction: Level 1 — two `Protocol`s, one implementation each
- State: zero — RIS in / RIS out, no cache, no DB
- Backend: RIS file roundtrip; Zotero SQLite/Web-API deferred

## Next actions (in order)

1. Pick a license (MIT or Apache-2.0); commit `LICENSE`.
2. Work tickets `0001` → `0005` in dependency order via TDD.
3. End-to-end smoke test: `make scan INPUT=…/ArchiveCCS.ris`, eyeball the diff.

## Tickets

| ID | Title | Depends on |
|----|-------|------------|
| 0001 | RIS roundtrip + data model + config loader | — |
| 0002 | Detect gaps | 0001 |
| 0003 | Resolve via OpenAlex | 0001 |
| 0004 | Resolve via Crossref | 0001 |
| 0005 | CLI pipeline + integration test on ArchiveCCS.ris | 0001, 0002, 0003, 0004 |

## Blockers

None. Code generation unblocked.

## Background

MAIBA was conceived 2026-04-28 while indexing the CCS PDF archive at
`/home/haduong/CNRS/html/ArchiveCCS/`. The exercise revealed that even a clean
RIS export had records with `AU - et al.`, missing dates, and missing DOIs that
regex couldn't fix. A janitor was needed; none existed in the form imagined.
