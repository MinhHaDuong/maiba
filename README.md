# MAIBA — My AI Bibliography Assistant

A standalone command-line assistant for reference managers (initially Zotero) that detects
incomplete records and fixes them with web research, with room to grow into deduplication,
normalization, full-text attachment, link discovery, light RAG, visualization, and
auto-extension.

minh.ha-duong@cnrs.fr

## Vision

A reference library is a slowly-rotting graph of bibliographic objects. Every entry has
gaps (missing date, partial author list, no DOI, untitled abstract), inconsistencies
(`van der Berg` vs `Van Der Berg`, title case drift across languages), and dead pointers
(broken URLs, unattached PDFs). Existing tools fix one symptom at a time inside the host
application; none do a sustained, agentic janitor pass over the whole collection.

MAIBA is that janitor. It scans a Zotero collection (or any RIS / BibTeX / CSL-JSON
file), classifies what's wrong, queries open scholarly metadata APIs, escalates to an LLM
only when needed, and writes back — with provenance tags so every change is reviewable
and reversible.

The first deliverable is a single command: `maiba scan --collection MyArchive` →
prints incomplete records and their candidate fixes. Everything else is incremental.

## MVP scope

One command. Reads `/home/haduong/CNRS/html/ArchiveCCS/ArchiveCCS.ris`, calls
**OpenAlex** then **Crossref** for records with gaps (missing title, author list,
date, DOI), and writes back a corrected RIS with provenance lines. No LLM by
default. Zero persistent state by default; pass `--cache` to enable an
on-disk HTTP response cache at `~/.cache/maiba/http/` (deletable; wipe via
`maiba clear-cache`). Tunables live in `config/maiba.yaml` — no hardcoded
constants in code.

That's the whole MVP. Everything below is roadmap, not commitment.

## Capability roadmap (KISS, do them in order)

1. **Detect** incomplete records *(MVP)*
2. **Resolve** via OpenAlex + Crossref *(MVP)*
3. **Apply** fixes with provenance tags in the output *(MVP)*
4. **LLM fallback** — opt-in, OpenRouter cloud or padme local
5. **Zotero SQLite / Web API** backend (currently RIS-only)
6. **Dedup** — title+author+year buckets → review queue
7. **Normalize** author name forms; title case per language
8. **Attach** open-access full text (Unpaywall) and OCR image-only PDFs
9. **Discover** related work and citation networks
10. **Embed** + light RAG over the user's library
11. **Visualize** the collection as a graph
12. **Auto-extend** — suggest items to add based on what's already in

The point is that 1–3 already justify the tool.

## Status

Pre-alpha. Project scaffold only. **No code yet.** See `ARCHITECTURE.md` §2 for
the four open decisions that gate code generation, and `STATE.md` for the
current goal and next actions.

## Repository layout

```
maiba/
├── README.md              this file: vision and orientation
├── ARCHITECTURE.md        open design discussion (read before writing code)
├── STATE.md               current goal, blockers, next actions (Imperial Dragon)
├── AGENTS.md              instructions for AI agents working on the repo
├── CLAUDE.md              imports AGENTS.md (Imperial Dragon convention)
├── Makefile               entrypoints; uses `uv run`, never bare pip/venv
├── pyproject.toml         dependencies and tool config (managed by uv)
├── src/maiba/             Python package (empty placeholder for now)
├── tests/                 pytest suite (empty placeholder for now)
├── tickets/               %erg v1 local tickets (see .claude/rules/tickets.md)
│   ├── archive/
│   └── tools/go/          erg validator source
├── .claude/               agent rules, skills, settings (Imperial Dragon + git-erg)
└── .git/hooks/            pre-commit ticket validation
```

## Quick start

There is nothing to run yet. Once code lands, the workflow will be:

```bash
make setup          # install deps via uv
make help           # list targets
uv run maiba --help # CLI entry point (when implemented)
```

## Conventions

- Toolchain: **`uv`**. Never `pip`, never bare `venv`, never `python -m venv`.
  Invoke Python via `uv run` so the virtualenv is implicit and reproducible.
- Build tasks: **`make`**. The Makefile is the single source of truth for
  named targets; CI and humans use the same recipes.
- Workflow: **Imperial Dragon** five-claw (Imagine → Plan → Execute → Verify → Reflect).
  See `AGENTS.md`.
- Tickets: **`%erg v1`** local files in `tickets/`. See `.claude/rules/tickets.md`.
- License: **CeCILL-B v1** (CEA-CNRS-INRIA Logiciel Libre, BSD-equivalent,
  GPL-compatible). See `LICENSE`.

## Related work

- **Zotero built-ins:** *Retrieve Metadata for PDF*, *Find Available PDF*, *Add by Identifier*
- **Plugins:** Better BibTeX, Aria (`lifan0127/ai-research-assistant`), Beaver, Zotero MCP, Zoplicate, ZotMoov
- **CLI:** `betterbib` (BibTeX-only), `pyzotero` (Zotero Web API), `anystyle` (Ruby parser)
- **APIs:** Crossref, OpenAlex, Semantic Scholar, arXiv, DataCite, Unpaywall

MAIBA's wedge is the *scan + autofix loop with provenance*, which none of the above
expose as a single batch operation.
