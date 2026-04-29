# State

Last updated: 2026-04-29 (session wrap: tickets 0014 0028 0029 0030 0031 merged)

## Current goal

**LLM-fallback path for grey-literature records.** The mechanical
resolver path is at its ceiling: 7/20 fixes on `ArchiveCCS.ris`. The
remaining 13 records are mostly French ministry meeting notes, NGO
reports, and other grey lit that are not in OpenAlex or Crossref. The
LLM resolver (0015) needs PDF first-page text (0014) as input and
audit/cost-control wrappers (0021, 0022) before it lands. Review
queue (0016) closes the loop.

## Status: mechanical recall at ceiling; LLM path is next milestone

CLI runs end-to-end and is Unix-pipeable:

```bash
maiba scan -v -i FILE.ris -o OUT.ris [--cache]   # rich logs
cat FILE.ris | maiba scan > OUT.ris              # stream-friendly
maiba clear-cache                                # cache wipe
```

113 tests green. Lint clean. Auth path verified end-to-end (`Bearer`
header reaches OpenAlex). Resolver chain is rate-limit-tolerant
(OpenAlex 429 doesn't abort; Crossref takes over). DEBUG output at
`-vv` shows top-3 candidates per record with the winning candidate
marked `*`.

PDF pipeline landed (tickets 0014, 0028, 0030): first-page text
extraction, embedded XMP/info-dict metadata, and pre-resolver DOI
scan. Pipeline merge now fills all resolver-returned fields
opportunistically (ticket 0029). OpenAlex Work IDs captured as
`OAID` field and round-tripped via RIS `C1` tag (ticket 0031).

Real-world recall on canonical corpus (`tests/fixtures/ArchiveCCS.ris`):
**7 of 20** records fixed. Mostly `PY` and `AU` fills via OpenAlex or
Crossref title+author search.

`OPENROUTER_API_KEY` is now in `.env`. Ticket 0015 (LLM resolver)
has no remaining blockers.

## Open tickets

| ID | Title | Blocked by |
|----|-------|------------|
| 0015 | LLM-based metadata resolver for grey literature | — |
| 0016 | Review queue: write low-confidence fixes to markdown | 0015 |
| 0021 | Pre-flight cost estimate and interactive confirm for `--llm-fallback` | 0015 |
| 0022 | Per-run JSONL audit log of every LLM call | 0015 |
| 0032 | Fix test_pdf_metadata.py tests that reference non-committed corpus PDFs | — |

## Next actions (in order)

1. **0032** — small hygiene: 4 tests in `test_pdf_metadata.py` reference
   non-committed corpus PDFs and fail in worktrees. Fix before 0015 adds more.
2. **0015** — LLM resolver. No blockers. `OPENROUTER_API_KEY` is in `.env`.
   PDF first-page text (0014) and metadata (0028) are available as context.
3. **0021 + 0022** — cost guardrails before any large run with the
   LLM resolver enabled.
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
