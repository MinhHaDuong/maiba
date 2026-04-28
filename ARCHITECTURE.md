# MAIBA — Architecture

Read `README.md` first. This document is the design contract for the MVP:
the open questions in §2 were locked on 2026-04-28 (see §9 for the log) and
the `Item` data model in §6 is frozen for tickets 0001–0005. New decisions
are appended to §9 with a date. Nothing in §3–§8 is mutable without a
corresponding §9 entry.

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

## 2. Design questions (all DECIDED 2026-04-28 — see §9 for the log)

These four questions originally blocked the first line of code. All four are now
resolved with the user. Subsections are kept as the rationale record — read them
to understand *why* the answer is what it is, not to debate them again. KISS:
pick the smallest answer that meets the present need; widen later when the pain
is concrete.

### 2.1 User interface — DECIDED: A (pure CLI for MVP)

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

**Decided:** A. See §9.

---

### 2.2 Plugin / abstraction depth — DECIDED: Level 1 (two protocols, one impl each)

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

**Decided:** Level 1. See §9.

---

### 2.3 State persistence — DECIDED: zero state for MVP

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

**Decided:** zero state. See §9.

---

### 2.4 Library backend for MVP — DECIDED: A (RIS file roundtrip)

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

**Decided:** A. See §9.

---

## 3. Data flow

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

## 6. Item data model — frozen contract for tickets 0001–0005

The `Item` pydantic model is the single in-memory currency that flows from
RIS → detect → resolve → apply → RIS. It must accommodate (a) every RIS tag
seen in `ArchiveCCS.ris` and (b) every field MAIBA writes back from
OpenAlex / Crossref. This contract is frozen here so tickets 0001 (data model)
and 0003/0004 (resolvers) cannot drift.

### 6.1 RIS tags actually present in `ArchiveCCS.ris` (counts)

```
TY 223  TI 223  KW 223  ER 223  AU 465 (multi)  L1 226 (multi)
PY 213  LA  41  JO  40  PB  39  DO  24  T2  22
VL  20  SP  20  EP  20  DA  18  N1   4  UR   3  IS   1  CY   1
```

### 6.2 `Item` field map

| `Item` field | Type | RIS tag | OpenAlex path | Crossref path |
|---|---|---|---|---|
| `id` | `str` | derived from `L1` basename (e.g. `Ashworth.ea-2009-EngagingThePublic…`) | n/a — internal | n/a — internal |
| `TY` | `str` (enum) | `TY` | `type` (mapped) | `type` (mapped) |
| `TI` | `str` | `TI` | `title` | `title[0]` |
| `AU` | `list[str]` | `AU` (repeated) | `authorships[*].author.display_name` | `author[*]` → `"{family}, {given}"` or `name` for corporate |
| `PY` | `int \| None` | `PY` | `publication_year` | `published-print.date-parts[0][0]` ?? `published-online.date-parts[0][0]` ?? `issued.date-parts[0][0]` |
| `DA` | `str \| None` | `DA` | `publication_date` (`YYYY-MM-DD`) | reconstructed from same date fields if all 3 parts present |
| `JO` | `str \| None` | `JO` | `primary_location.source.display_name` (was `host_venue.display_name`; both must be tried) | `container-title[0]` |
| `T2` | `str \| None` | `T2` | n/a (use `JO` for now) | `container-title[0]` (book/proceedings) |
| `VL` | `str \| None` | `VL` | `biblio.volume` | `volume` |
| `IS` | `str \| None` | `IS` | `biblio.issue` | `issue` |
| `SP` | `str \| None` | `SP` | `biblio.first_page` | `page` split on `-` first part |
| `EP` | `str \| None` | `EP` | `biblio.last_page` | `page` split on `-` second part |
| `DO` | `str \| None` | `DO` | `doi` (strip `https://doi.org/` prefix) | `DOI` |
| `UR` | `str \| None` | `UR` | `id` or `primary_location.landing_page_url` | `URL` |
| `LA` | `str \| None` | `LA` | `language` (ISO 639-1, e.g. `"en"`) | `language` (ISO 639-1) |
| `KW` | `list[str]` | `KW` (repeated) | `keywords[*].display_name` | `subject[]` |
| `AB` | `str \| None` | absent in ArchiveCCS but allowed | reconstructed from `abstract_inverted_index` | `abstract` (rare) |
| `PB` | `str \| None` | `PB` | `primary_location.source.publisher` | `publisher` |
| `CY` | `str \| None` | `CY` | n/a | n/a |
| `L1` | `list[str]` | `L1` (repeated) | n/a — internal | n/a — internal |
| `N1` | `list[str]` | `N1` (repeated) | n/a — provenance lines live here | n/a — provenance lines live here |

### 6.3 Notes on shape variation

- **Crossref dates.** Use this priority order: `published-print.date-parts` →
  `published-online.date-parts` → `issued.date-parts` → `created.date-parts`.
  Each is a list-of-list-of-int that may be 1, 2, or 3 elements deep.
- **OpenAlex venue moved.** `host_venue` exists on older endpoints; newer
  responses put the same data under `primary_location.source`. Try both.
- **Crossref title is an array.** Always take `[0]`; sometimes there's a
  `subtitle` array — concatenate as `"title: subtitle"` only if both nonempty.
- **OpenAlex DOI prefix.** The `doi` field is a full URL
  (`https://doi.org/10.1016/...`). Strip the prefix when populating `Item.DO`.
- **Authors can be corporate.** Crossref returns `{"name": "ADEME"}` (no
  `family`/`given`) for corporate authors. OpenAlex returns the same as a
  single `display_name`. Map to a single-element `AU`.
- **OpenAlex abstract is inverted.** `abstract_inverted_index` is a dict
  `{word: [positions]}`. Reconstruct only if the user asks for `AB`.

### 6.4 `Item.id` — keying convention

`id` is derived from the `L1` basename without extension:

```
file:///home/haduong/CNRS/html/ArchiveCCS/Ashworth.ea-2009-EngagingThePublic….pdf
                                          └────────────────────┬─────────────┘
                                                                └─→ Item.id
```

Reasoning: every record in `ArchiveCCS.ris` already has a unique `L1`
basename (the existing archive convention), so no additional ID generation
is needed. If `L1` is missing, `id` falls back to the SHA-1 of `(TI, AU[0],
PY)` — guaranteed-stable across runs but never exposed in the RIS.

### 6.5 What lives in `Item.N1` (provenance)

When MAIBA modifies a record, it appends to `N1`:

```
maiba:autofixed:2026-04-28 source=openalex confidence=0.93
maiba:before AU=["Ashworth, P.", "et al."]
maiba:before JO=
```

These lines are emitted as separate `N1  - …` entries in the output RIS.

## 7. Stack

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

## 8. Configuration (no hardcoded constants — see §0)

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

## 9. Decisions log

- **2026-04-28 — UI shape (§2.1) → DECIDED: A.** Pure CLI for MVP. No TUI, no
  web UI. One verb per command, machine-readable output where useful.
- **2026-04-28 — Abstraction depth (§2.2) → DECIDED: Level 1.** Two Python
  `Protocol`s — `LibraryBackend` and `MetadataResolver` — with one
  implementation each. No entry-points, no plugin registry, no event bus.
  Add a second implementation only when a real second case shows up.
- **2026-04-28 — State persistence (§2.3) → DECIDED: zero state.** RIS in →
  RIS out. No DB, no run log, no resume file. If runtime grows past ~30 s
  on `ArchiveCCS.ris`, add an HTTP response cache that is safe to delete.
- **2026-04-28 — Library backend for MVP (§2.4) → DECIDED: A.** RIS file
  roundtrip. Zotero SQLite/Web-API write-back deferred until post-MVP.
- **2026-04-28 — Resolver order → DECIDED:** OpenAlex first, then Crossref.
  Configurable in `config/maiba.yaml` (`resolvers.order`).
- **2026-04-28 — LLM fallback → DECIDED:** opt-in only via `--llm-fallback`,
  off by default. OpenRouter for cloud, padme HTTP for local. Disabled in MVP.
- **2026-04-28 — Item data model contract (§6) → FROZEN.** RIS tag, OpenAlex
  path, Crossref path mapping locked. Tickets 0001/0003/0004/0005 share this
  single contract; resolvers do not invent fields. Shape variation handled
  in mapping (Crossref date priority, OpenAlex `host_venue` →
  `primary_location.source`, corporate author `name`-only entries, OpenAlex
  `abstract_inverted_index`).
- **2026-04-28 — `Item.id` derivation (§6.4) → DECIDED.** `L1` basename
  without extension (matches the existing ArchiveCCS naming convention).
  Fallback: SHA-1 of `(TI, AU[0], PY)` if `L1` is absent. Never written to RIS.
- **2026-04-28 — Provenance representation (§6.5) → DECIDED.** When MAIBA
  modifies a record, prepend `N1  - maiba:autofixed:DATE source=… confidence=…`
  plus one `N1  - maiba:before FIELD=…` per modified field. Stays inside the
  RIS file — no sidecar, no separate journal (consistent with the zero-state
  decision above).
- **2026-04-28 — Test contract grounded in real API responses → DECIDED.**
  Ticket 0006 captured 12 frozen JSON fixtures
  (`tests/fixtures/responses/{openalex,crossref}/`). Resolver tests replay
  these via `respx`; they are **never re-recorded automatically**. Upstream
  shape changes surface as test failures, prompting deliberate re-capture.
- **2026-04-28 — RIS whitespace tolerance → DECIDED.** Parser accepts both
  the canonical two-space (`XX  - `) and single-space (`XX - `) tag
  separator forms on input. Output always emits the canonical two-space
  form. Vendors disagree on the spec; rejecting single-space would break
  legitimate imports.
- **2026-04-28 — Retrospective tickets → SCOPED.** Same-session
  `created → claimed → status closed` is acceptable only for pre-flight
  scaffolding the user explicitly requests (precedent: ticket 0006). All
  changes under `src/maiba/` must execute through orchestrator TDD.
  See `AGENTS.md` "Retrospective tickets".
- **2026-04-28 — License → DECIDED: CeCILL-B v1.** CEA-CNRS-INRIA Logiciel
  Libre, BSD-equivalent, GPL-compatible, French-law jurisdiction. Chosen
  for institutional alignment with CNRS while keeping adoption friction at
  permissive-license levels. SPDX identifier: `CECILL-B`. Official text in
  `LICENSE` (515 lines, fetched from spdx/license-list-data).

## 10. Glossary

- **Gap** — a missing or empty bibliographic field in an item
- **Resolver** — a service that maps `(title, authors, year)` → metadata (Crossref, …)
- **Confidence** — float in [0, 1]; threshold is `--apply-threshold` (default 0.85)
- **Provenance tag** — Zotero tag added by MAIBA so a human or another agent can
  audit, accept, or revert a change
