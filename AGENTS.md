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
| `~/.claude/skills/` | Generic skills (celebrate, review-pr, memory, etc.) |
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

## Imperial Dragon workflow (five claws)

Every non-trivial task passes through five phases. Announce transitions inline:
`[Phase → Phase] reason`.

### Imagine
Interactive discussion on an `explore-{topic}` branch. Surface motivations and
options, challenge assumptions. Deliverable: a shared vision plus tickets, a
small fix, or nothing actionable (delete the branch).

### Plan
Write the ticket(s) with full context and the first failing test. Specify exit
criteria. No production commits yet.

### Execute
Fresh context, ticket as sole input. TDD: red → green → refactor. Atomic commits.
Tests must pass before merging.

### Verify
Run `/verify` (adherence + review + simplify). Anti-rubber-stamp: every exit
criterion is checked against the actual diff. Returns APPROVED / REROLL / ESCALATE.

### Reflect
After merge, `/celebrate` updates `STATE.md`, archives stale tickets, runs the
healthcheck. Lessons go to memory.

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
