# AI Agent Guidelines for MAIBA

> `CLAUDE.md` contains only `@AGENTS.md` — keep it that way.

## Read first

1. `README.md` — vision and orientation
2. `ARCHITECTURE.md` — open design questions (do not write code that pre-empts them)
3. `STATE.md` — current goal, blockers, next actions

## Configuration

| Location | Purpose |
|----------|---------|
| `~/.claude/rules/` | Generic rules (git, workflow, coding, state-roadmap) |
| `~/.claude/skills/` | Generic skills (hunt, roar, review-pr, verify-gate, …) |
| `~/.claude/hooks/` | Generic hooks |
| `.claude/rules/` | Project-specific rules (currently: `tickets.md` only, from git-erg) |
| `.claude/skills/` | Project-specific skills (ticket-* from git-erg) |
| `.claude/settings.json` | Project permissions and validation hooks |
| `.claude/CLAUDE.md` | Auto-managed by git-erg — do not hand-edit between markers |

## Conventions (must follow)

### Toolchain

- **`uv`** for everything Python. Never `pip`, never bare `python -m venv`,
  never `python -m pip`. Activate the virtualenv implicitly via `uv run`.
- **`make`** for entrypoints. The Makefile is the single source of truth for
  named targets. CI and humans use the same recipes.
- **`pyproject.toml`** is the dependency manifest. Edit it directly; let `uv`
  manage the lockfile.

### Code

- Python 3.11+ (matches the rest of Minh's projects).
- `pydantic` for data models, `httpx` for HTTP, `rapidfuzz` for string sim.
- KISS. No premature abstraction. Two implementations earn an interface;
  one does not. See `ARCHITECTURE.md` §2.2.
- Tests live under `tests/`. Use recorded HTTP cassettes (`vcrpy`) for resolver
  tests so they are deterministic and offline-runnable.

### Tickets (`%erg v1`)

This project uses git-erg local tickets for work coordination. See
`.claude/rules/tickets.md` for the spec. Slash commands:

- `/ticket-new [title]` — create a ticket
- `/ticket-ready` — list unblocked, unclaimed tickets
- `/ticket-claim [id]` — claim a ticket for work
- `/ticket-close [id]` — close a ticket
- `/ticket-release [id]` — release a claimed ticket

GitHub Issues are reserved for cross-repo or human-facing coordination.

#### Retrospective tickets

A ticket whose log shows `created → claimed → status closed` all in one
session is acceptable **only** for pre-flight scaffolding work the user
explicitly asked to be done immediately (e.g. ticket 0006, capturing API
fixtures). For production code — any change under `src/maiba/` — the
orchestrator must execute the ticket in TDD: open the ticket first, write
the failing test, make it pass, then close. Do not pre-write code and
backfill a closed ticket.

## Workflow

The generic workflow (phases, worktrees, TDD, escalation, git discipline) lives
in the harness rules under `~/.claude/rules/`, loaded into every session, and
skills are listed in each session's skill catalog. Do not copy it back here: the
copy drifts. This file once pointed at `/verify` and `/celebrate`, neither of
which exists any more.

### Verify in proportion to what can break

Before merging, decide which checks the change needs and state them on the PR:

- **Tickets, docs, config**: `make lint` (or the ticket validator), and a read of the result.
- **Code under `src/maiba/`**: tests for the changed behaviour, then `make check`.

Anything beyond tickets and docs gets at least one independent reviewer on a
model other than the coder's (`/review-pr`, scoped to the risk). Then
`/verify-gate` checks every exit criterion against concrete evidence (commit SHA
+ file:line, or a test id). Two review rounds at most, then escalate.

## Safety

- Never write to a real Zotero library in a test. Use a sandbox SQLite copy
  or RIS roundtrip.
- Never call paid LLM APIs from a test. The default code path must be free
  and deterministic — LLM is opt-in via `--llm-fallback`.
- Always tag MAIBA writes with provenance (`maiba:autofixed:DATE`,
  `maiba:source:RESOLVER`, `maiba:confidence:F`) so a human can audit and revert.
- Hard-fail rather than silently fabricate metadata. A missing field is better
  than a wrong field.

## When stuck

- Re-read `ARCHITECTURE.md`. Most blockers come from making a decision the
  document explicitly defers.
- Use the advisor tool for second opinions on design crossroads.
- Open a ticket describing the unknown rather than guessing.
