# State

Last updated: 2026-04-28

## Current goal

**Close the mechanical-resolver recall path on `ArchiveCCS.ris`.**
Real run today produces 2 of 20 fixes despite tickets 0012 (auth) +
0013 (scorer fix) merging. Two diagnosed bugs are queued (0023, 0024)
that should lift recall to ~7-8 of 20 — the JOUR ceiling, not yet
the grey-lit ceiling.

The LLM-fallback path (0014, 0015, 0016, 0021, 0022) is **deferred to
a later session.** It's the path to the remaining ~12 grey-lit
records, but it introduces real cost variance and audit obligations
that warrant fresh attention. The tickets are written and queued in
dependency order; resume by picking them up when the mechanical path
is at its ceiling and the dev iteration loop has settled.

## Status: post-MVP, iterating on recall

MVP shipped (tickets 0001–0005). CLI runs end-to-end:
`uv run maiba scan FILE.ris -o OUT.ris [--apply] [--cache]`. Tests
pass. Hygiene ratchets in place (no print, no hardcoded URLs/emails,
no NotImplementedError/skip/TODO without `# noqa: hygiene`).

Real-world recall on the canonical corpus: 2 of 20. Diagnosis below.

## Diagnostic from today's session

Real run + REPL probe revealed two distinct issues in the 18 misses:

1. **OpenAlex auth not reaching the resolver in practice.** REPL
   showed `OPENALEX_API_KEY` empty when imports ran, every OpenAlex
   call returning HTTP 429 (rate-limited on the $0 free tier).
   Either ticket 0017's `load_dotenv` doesn't run before the
   resolver imports, or the user-facing scan also hits this.
   → **Ticket 0023** adds startup observability + load-order test.

2. **Crossref short-title search is noisy.** Direct probe for
   "Incentivising CCS in the EU" returned wrong candidates in top-5
   ("EU executive launches CCS support network", "Incentivising
   Angels", etc.). The right paper is buried beyond the window.
   The shared scorer correctly rejects the noise; the fix is in
   query construction (year filter + larger rows + author hint).
   → **Ticket 0024** addresses this.

After 0023 + 0024 land + a re-run, expected recall on the JOUR
subset: 6-7 of 7. Total expected across all gaps: ~7-9 of 20.
Remaining 11-13 are grey lit (RPRT/NEWS/ICOMM) — the LLM territory,
deferred.

## Next actions (in order)

1. **Wait for orchestrator** to pick up 0023 (env loading
   observability). When the verbose log line appears at startup, the
   real auth state is finally observable.
2. **0024** lands next (Crossref query expansion). Independent of
   0023 — could land in either order.
3. **Re-measure on `ArchiveCCS.ris`.** Re-run `uv run maiba scan -i
   tests/fixtures/ArchiveCCS.ris -o test.ris --cache -v`, count
   fixes. Document delta vs. today's 2/20 baseline.
4. **Decide LLM resume timing** based on the new recall number.
   If ~8/20, the LLM tickets become the next priority. If something
   below 7/20, there's another mechanical bug to find first.

## Deferred tickets (LLM-fallback path)

In dependency order, ready when the user wants to resume:

- 0014 — Extract PDF first-page text from `L1` link
- 0015 — LLM resolver (depends on 0014)
- 0016 — Review queue for low-confidence cases (depends on 0015)
- 0021 — Pre-flight cost estimate + interactive confirm (depends on 0015)
- 0022 — Per-run JSONL audit log (depends on 0015)

The PDFs are still on disk at `/home/haduong/CNRS/html/ArchiveCCS/`
(restored after the trash-and-untrash cycle). `OPENROUTER_API_KEY`
is not yet in `.env`; the user adds it when they're ready to spend.

## Blockers

None. Orchestrator can pick up 0023 / 0024 immediately.

## Background

MAIBA was conceived 2026-04-28 while indexing the CCS PDF archive at
`/home/haduong/CNRS/html/ArchiveCCS/`. The exercise revealed that
even a clean RIS export had records with `AU - et al.`, missing
dates, and missing DOIs that regex couldn't fix. A janitor was
needed; none existed in the form imagined.
