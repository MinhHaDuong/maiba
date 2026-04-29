# State

Last updated: 2026-04-29 (housekeeping run 06:55Z)

## Current goal

**LLM-fallback path for grey-literature records.** The mechanical
resolver path is at its ceiling: 7/20 fixes on `ArchiveCCS.ris`. The
remaining 13 records are mostly French ministry meeting notes, NGO
reports, and other grey lit that are not in OpenAlex or Crossref. The
LLM resolver (0015) needs PDF first-page text (0014) as input and
audit/cost-control wrappers (0021, 0022) before it lands. Review
queue (0016) closes the loop.

## Status: mechanical recall path at ceiling

CLI runs end-to-end and is Unix-pipeable:

```bash
maiba scan -v -i FILE.ris -o OUT.ris [--cache]   # rich logs
cat FILE.ris | maiba scan > OUT.ris              # stream-friendly
maiba clear-cache                                # cache wipe
```

87 tests green. Lint clean. Auth path verified end-to-end (`Bearer`
header reaches OpenAlex). Resolver chain is rate-limit-tolerant
(OpenAlex 429 doesn't abort; Crossref takes over). DEBUG output at
`-vv` shows top-3 candidates per record with the winning candidate
marked `*`.

Real-world recall on canonical corpus (`tests/fixtures/ArchiveCCS.ris`):
**7 of 20** records fixed. Mostly `PY` and `AU` fills via OpenAlex or
Crossref title+author search.

## Open tickets

| ID | Title | Blocked by |
|----|-------|------------|
| 0014 | Extract PDF first-page text from L1 link | — |
| 0015 | LLM-based metadata resolver for grey literature | 0014 |
| 0016 | Review queue: write low-confidence fixes to markdown | 0015 |
| 0021 | Pre-flight cost estimate and interactive confirm for `--llm-fallback` | 0015 |
| 0022 | Per-run JSONL audit log of every LLM call | 0015 |
| 0028 | Extract PDF embedded metadata (XMP / info dict) — sibling to 0014 | — |
| 0029 | Pipeline merge step drops derived fields outside the gap set | — |
| 0030 | Extract DOI from PDF first-page text before resolver search | 0014 |
| 0031 | Capture OpenAlex Work IDs (W…) on the Item model | — |

## Next actions (in order)

1. **0014** — read first-page text from L1 PDFs into a sidecar cache.
   Independent of every other open ticket.
2. **0028** — XMP/info dict metadata. Same input domain as 0014;
   could be combined or kept separate. Decide at execution time.
3. **0015** — LLM resolver consuming 0014's text. `OPENROUTER_API_KEY`
   needs to land in `.env` before this is testable end-to-end.
4. **0021 + 0022** — cost guardrails before any large run with the
   LLM resolver enabled.
5. **0016** — review queue for the residue.

## Blockers

None. PDFs are on disk at `/home/haduong/CNRS/html/ArchiveCCS/`.
`OPENROUTER_API_KEY` is the only thing the user needs to add to
`.env` before 0015 becomes testable, and that's a one-line change.

## Background

MAIBA was conceived 2026-04-28 while indexing the CCS PDF archive at
`/home/haduong/CNRS/html/ArchiveCCS/`. Even a clean RIS export had
records with `AU - et al.`, missing dates, and missing DOIs that
regex couldn't fix. A janitor was needed; none existed in the form
imagined. Today: the mechanical janitor handles ~35% of the gappy
records on this corpus; the LLM janitor is the next milestone.
