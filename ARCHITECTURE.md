# MAIBA — Architecture (open discussion, not yet decided)

This document is a working draft. It frames the design decisions that gate the first
line of code. Read `README.md` first. Nothing here is final — entries marked **DECIDED**
have user sign-off; everything else is a question.

## 0. MVP target (user, 2026-04-28)

Concrete success criterion: a single `make` target that reads
`/home/haduong/CNRS/html/ArchiveCCS/ArchiveCCS.ris` and writes a corrected RIS with
provenance lines, in under a minute, using only Crossref + OpenAlex (no LLM).

Everything in this document is filtered by: *does it bring the MVP closer or further?*

### Hard constraints from the user
- **No hardcoded constants.** API endpoints, mailto address, gap definitions,
  confidence thresholds, field weights, retry counts → all live in YAML under
  `config/`. Code reads `config/maiba.yaml` (and possibly siblings).
- **Minimize state.** Every cache, log, sidecar, or run database is a liability.
  Prefer pure functions over memory. The MVP target is *zero* persistent state:
  RIS in → RIS out, network calls are non-cached, nothing on disk between runs.
  If a cache later proves load-bearing, it must be safe to `rm -rf` without
  breaking correctness.
- **LLM is opt-in.** Default path uses only OpenAlex + Crossref. LLM (OpenRouter
  cloud or padme local) only fires behind `--llm-fallback`.
- **API patterns reference:** `Climate Finance/scripts/catalog_openalex.py` and
  the `utils.polite_get` / `MAILTO` idiom there. Reuse the *style*, not the code.

## 1. Scope

What MAIBA *is*: a janitor for a reference library. Detect incomplete records, resolve
via web APIs, write back with provenance. Iteratively grow capability.

What MAIBA *isn't* (today): a Zotero replacement, a citation generator, a PDF reader,
a writing assistant. Adjacent, not overlapping.

## 2. Open questions for discussion

These two questions block the first line of code. KISS — pick the smallest answer that
meets the present need; widen later when the pain is concrete.

### 2.1 User interface

What does the user actually type / click to run MAIBA? Three plausible shapes, ordered
from least to most code:

#### Option A — Pure CLI, no state

```
maiba scan path/to/library.ris > report.md
maiba fix --apply --collection MyArchive
```

- One command per verb, exits when done. Reads RIS / BibTeX / CSL-JSON / Zotero SQLite.
- Output: machine-readable JSON or human Markdown.
- Pros: KISS to the bone. Composes with shell, cron, make, git. Easy to test.
- Cons: No persistent session, so each run re-discovers the library. No interactive
  fix-or-skip review (you'd need a separate `maiba review` that opens an editor).

#### Option B — CLI with interactive review (TUI)

```
maiba scan path/to/library.ris       # writes report
maiba review report.json             # opens an interactive picker (rich/textual)
                                     # user accepts/rejects/edits each fix
```

- Same as A, plus a `review` subcommand that opens a terminal picker for the human
  decision step. Library: `prompt_toolkit`, `rich.prompt`, or `textual`.
- Pros: Keeps the unattended path (A) but adds a curation loop where the
  cost-of-being-wrong is highest. Still no daemon, no server, no session state.
- Cons: One extra dependency. TUI taste varies.

#### Option C — Local web UI

```
maiba serve --port 8765   # opens a browser, shows the library, click-to-fix
```

- A minimal FastAPI / Flask app serving an HTML page over localhost.
- Pros: Pretty, multi-pane, can show graphs and PDFs.
- Cons: Lots of code. Frontend tooling. Auth. Lifecycle management. **Overkill for v1**.

#### Recommendation

**A for v0, A+B for v1.** Start with the unattended pipeline; add the review TUI when
the first user (you) feels the pain of editing JSON by hand. Skip the web UI until
visualization (capability #9) lands and actually needs a canvas. If you decide later
to build a Zotero plugin, it is essentially a thin native UI over the same CLI core
— so don't paint yourself into a Python-only corner.

**Decision needed:** confirm A for v0, defer B and C, or pick a different shape.

---

### 2.2 Plugin / abstraction depth

How much of the system should be pluggable on day 1? The choices ladder up in cost:

#### Level 0 — No plugins

Hard-code Zotero as the backend, Crossref as the resolver, English/French as the
languages, RIS as the import/export format. Do one thing, well, for one user.

- Pros: Tiniest codebase. Tightest tests. Fastest to v0.
- Cons: Adapting to Mendeley / EndNote / Hypothesis later means rewriting.

#### Level 1 — Two thin interfaces, hand-coded implementations

Define two Python protocols (`LibraryBackend`, `MetadataResolver`) with a single
implementation each. Add a second implementation only when a real second case shows up.

```python
class LibraryBackend(Protocol):
    def items_with_gaps(self) -> Iterator[Item]: ...
    def update(self, item_id: str, fields: dict) -> None: ...

class MetadataResolver(Protocol):
    def resolve(self, item: Item) -> ResolutionResult: ...
```

- Pros: Substitution is possible without ripping things up. Tests can use a fake.
- Cons: A whisper of indirection that costs maybe 30 lines.

#### Level 2 — Entry-points / registry

Use `importlib.metadata` entry points so third-party packages can register backends
and resolvers without touching MAIBA. Add a config file to enable/disable.

- Pros: Real ecosystem. Other people can write plugins.
- Cons: Lots of moving parts before there is even a user.

#### Level 3 — Pluggy / generic event bus

Full pre/post hooks per phase, configurable pipelines, etc.

- Pros: Power.
- Cons: You will have written a framework before you have a working janitor.

#### Recommendation

**Level 1.** Two protocols, one implementation each on day 1, with a one-line note
in the docstring that says "the second implementation is a YAGNI signal — wait until
a concrete second case exists before adding one." This keeps the code testable
(swap in a fake `LibraryBackend` for tests) without paying for an ecosystem that
hasn't shown up.

**Decision needed:** confirm Level 1, or argue for 0/2/3.

---

### 2.3 State persistence

How much does MAIBA remember between runs?

- **Zero state (recommended for MVP).** RIS in → RIS out. No DB, no run log, no
  resume file. Each invocation is a pure function of `(input.ris, config.yaml,
  current state of OpenAlex/Crossref)`. Re-running is cheap because the inputs
  are small; if it gets slow, *that* is when we add a cache.
- **HTTP response cache only.** Stash raw API responses on disk so re-runs are
  instant; correctness unaffected if you `rm -rf` it. Costs ~50 lines.
- **Full run journal.** Record every fix, every API call, every decision in a
  SQLite db so you can `maiba undo --run X`. Needed for SQLite backend writes
  but YAGNI for RIS roundtrip (the RIS file is its own audit trail when
  versioned in git).

**Recommendation:** zero state for MVP. Add response cache only when a run
takes more than ~30 seconds end-to-end on `ArchiveCCS.ris`.

**Decision needed:** confirm zero state.

---

### 2.4 Library backend for MVP

Which backend does the MVP support?

- **A — RIS file roundtrip.** Parse `*.ris`, fix items, emit `*.ris`. Lossy for
  Zotero-specific fields (tags, collections) but fine for `ArchiveCCS.ris` which
  is *already* an RIS file.
- **B — Zotero SQLite (read-write).** Talk directly to `zotero.sqlite`.
  Higher fidelity but: Zotero must be closed during writes, schema versions
  drift, attachment paths are fragile.
- **C — Zotero Web API via `pyzotero`.** Cleanest write path but requires an
  API key, network, and a synced library.

**Recommendation:** A for MVP — it matches the actual ArchiveCCS workflow
(your RIS is the source of truth, Zotero is a downstream consumer). Add B or C
later when your day-to-day work moves into Zotero.

**Decision needed:** confirm A.

---

## 3. Data flow (sketch, contingent on §2)

```
┌──────────────────┐     ┌──────────────┐     ┌────────────────┐
│ LibraryBackend   │ --> │ Detect gaps  │ --> │ Resolve via    │
│  (Zotero / RIS)  │     │ (rules)      │     │ web APIs       │
└──────────────────┘     └──────────────┘     └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │ Rank candidates│
                                              │ (string sim +  │
                                              │  author overlap)│
                                              └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐     ┌──────────────┐
                                              │ Confidence ≥ τ?├─yes→│ Apply with   │
                                              └────────────────┘     │ provenance   │
                                                       │ no          │ tag          │
                                                       ▼             └──────────────┘
                                              ┌────────────────┐
                                              │ Review queue   │
                                              │ (TUI or file)  │
                                              └────────────────┘
```

LLM step is optional and gated: only when API resolution fails *and* the user has
enabled `--llm-fallback`. Default is no LLM call so the tool is deterministic and free.

## 4. Provenance and reversibility (non-negotiable)

Every write to the library carries:
- `maiba:autofixed:YYYY-MM-DD` tag
- `maiba:source:<resolver>` tag (`crossref`, `openalex`, `llm:gpt-4`, ...)
- `maiba:confidence:<0..1>` tag
- The previous value of every modified field, in a `maiba:before` extra-field

The user must be able to revert *all* changes from one MAIBA run with a single
command (`maiba undo --run YYYY-MM-DDTHHMMSS`). This is harder than it looks for
the SQLite backend; it is trivial for RIS roundtrips. May influence §2.

## 5. Out of scope (until further notice)

- Group libraries / shared collections
- Citation style generation
- Writing assistance / draft generation
- Plagiarism / duplication detection across the open web
- Fine-tuning a custom model
- Mobile / web SaaS

## 6. Stack (proposed, not decided)

For MVP (RIS roundtrip, OpenAlex + Crossref, no LLM):

- Python 3.11+ (matches `aedist`)
- `uv` for env, `make` for entrypoints
- `pydantic` for data models, `httpx` for API calls (with `mailto` and rate-limit headers
  in the polite-pool style of Climate Finance's `utils.polite_get`)
- `rapidfuzz` for title / author similarity scoring
- `pyyaml` for `config/maiba.yaml`
- `pytest` + `respx` (httpx mock) for resolver tests — deterministic, offline

Deferred (do not import until the corresponding capability ticket lands):
- `pyzotero` — only when SQLite/Web-API backend is added (post-MVP)
- `rich` / `textual` — only if §2.1 picks Option B
- LLM SDKs — only when `--llm-fallback` is wired (OpenRouter for cloud, padme HTTP for local)

## 7. Configuration (no hardcoded constants — see §0)

The MVP reads `config/maiba.yaml`. Everything tunable lives there.
Sketch (subject to change in the design conversation):

```yaml
# config/maiba.yaml — MAIBA runtime configuration. No constants in code.

contact:
  mailto: minh.ha-duong@cnrs.fr     # used as User-Agent + OpenAlex polite-pool

http:
  timeout_s: 10
  max_retries: 3
  backoff_s: 1.5
  rate_limit_per_s: 5

resolvers:
  order: [openalex, crossref]       # tried in this order; first hit ≥ threshold wins
  openalex:
    base_url: https://api.openalex.org
  crossref:
    base_url: https://api.crossref.org

gaps:
  required_fields: [TI, AU, PY]      # an item is "incomplete" if any are missing
  recommended_fields: [DO, JO, AB]   # missing these triggers a softer fix attempt
  forbidden_authors: ["et al.", "Anonymous"]  # values that count as missing AU

matching:
  title_similarity_min: 0.85         # rapidfuzz token_sort_ratio threshold
  author_overlap_min: 0.5            # fraction of input authors found in candidate
  apply_threshold: 0.85              # below this, queue for review

llm:
  enabled: false                     # opt-in via --llm-fallback
  provider: openrouter               # or "padme"
  model: openai/gpt-4o-mini
  endpoint_padme: http://padme:11434

provenance:
  tag_prefix: "maiba"                # e.g. maiba:autofixed:2026-04-28
```

## 8. Decisions log

- _(empty — populate after each design conversation)_

## 9. Glossary

- **Gap** — a missing or empty bibliographic field in an item
- **Resolver** — a service that maps `(title, authors, year)` → metadata (Crossref, …)
- **Confidence** — float in [0, 1]; threshold is `--apply-threshold` (default 0.85)
- **Provenance tag** — Zotero tag added by MAIBA so a human or another agent can
  audit, accept, or revert a change
