# State

Last updated: 2026-04-29 (session wrap: tickets 0032 0033 fixed/decided; XMP crash patched)

## Current goal

**LLM-fallback path for grey-literature records.** The mechanical
resolver path is at its ceiling: 7/20 fixes on `ArchiveCCS.ris`. The
remaining 13 records are mostly French ministry meeting notes, NGO
reports, and other grey lit that are not in OpenAlex or Crossref. The
LLM resolver (0015) is unblocked and ready for the nightbeat.

## Status: worktree branch pending merge; nightbeat targets 0015

CLI runs end-to-end and is Unix-pipeable:

```bash
maiba scan -v -i FILE.ris -o OUT.ris [--cache]   # rich logs
cat FILE.ris | maiba scan > OUT.ris              # stream-friendly
maiba clear-cache                                # cache wipe
```

113 tests green on main. 114 on the pending worktree branch.
Lint clean. Auth path verified end-to-end. Resolver chain is
rate-limit-tolerant.

PDF pipeline (0014, 0028, 0030): first-page text, embedded XMP/info-dict
metadata, pre-resolver DOI scan. Pipeline merge fills all empty fields
(0029). OpenAlex Work IDs captured as `OAID` via RIS `C1` tag (0031).

**Design decision (0033, 2026-04-29):** embedded PDF metadata (`extract_pdf_metadata`)
is dead code in the pipeline — QA of 215 corpus PDFs confirmed it is
mostly garbage (Word filenames, internal usernames). Decision: pass it as
LLM context only in 0015, never write to item fields directly.

**Bug fixed (2026-04-29):** malformed XMP XML in real corpus PDFs caused an
unhandled `PdfReadError` in `extract_pdf_metadata`. Fixed with regression
test. On worktree branch `worktree-elegant-questing-squid`, pending merge.

Real-world recall on canonical corpus (`tests/fixtures/ArchiveCCS.ris`):
**7 of 20** records fixed. 24/215 PDFs have a DOI on the first page,
enabling a direct resolver lookup for those records.

`OPENROUTER_API_KEY` is in `.env`. Ticket 0015 has no remaining blockers.

## Open tickets

| ID | Title | Blocked by |
|----|-------|------------|
| 0015 | LLM-based metadata resolver for grey literature | — |
| 0016 | Review queue: write low-confidence fixes to markdown | 0015 |
| 0021 | Pre-flight cost estimate and interactive confirm for `--llm-fallback` | 0015 |
| 0022 | Per-run JSONL audit log of every LLM call | 0015 |

*(Tickets 0032 and 0033 are closed on the worktree branch, pending merge to main.)*

## Next actions (in order)

1. **Merge** `worktree-elegant-questing-squid` → main (0032 fix, XMP bug fix, 0033 closed).
2. **0015** — LLM resolver. No blockers. `OPENROUTER_API_KEY` in `.env`.
   PDF first-page text (0014) and embedded metadata (0028, LLM-context only)
   are available as evidence. 24 records have DOI from first page.
3. **0021 + 0022** — cost guardrails and audit log before any large run.
4. **0016** — review queue for the residue.

## Blockers

None.

## Background

MAIBA was conceived 2026-04-28 while indexing the CCS PDF archive at
`/home/haduong/CNRS/html/ArchiveCCS/`. Even a clean RIS export had
records with `AU - et al.`, missing dates, and missing DOIs that
regex couldn't fix. A janitor was needed; none existed in the form
imagined. Today: the mechanical janitor handles ~35% of the gappy
records on this corpus; the LLM janitor is the next milestone.
