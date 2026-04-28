# MAIBA test fixtures

| File | Purpose |
|------|---------|
| `ArchiveCCS.ris` | The real-world 223-entry corpus. Canonical fixture for unit, integration, and smoke tests. |
| `good.ris` | Hand-written 3-record RIS (JOUR + RPRT + NEWS) covering the type spread. Parser must accept; roundtrip must be lossless. |
| `empty.ris` | Zero bytes. Parser must return an empty iterator without raising. |
| `bad-notaris.ris` | Plain prose, no RIS tags. Parser must raise a clear `RisParseError`, not silently return empty. |
| `bad-no-er.ris` | Record without `ER  -` terminator. Parser must raise. |
| `bad-no-ty.ris` | Record without leading `TY  -`. Parser must raise. |
| `bad-malformed-tag.ris` | Tags with wrong separators (`AU -`, `T1:`, `PY  2009`, `DO=…`). Parser must raise. |
| `bad-truncated-mid-record.ris` | File ends mid-record after the first ER. Parser must raise on the second record (the first must still parse). |
| `bad-binaryfile.ris` | First 512 bytes of a real PDF, renamed to `.ris`. Realistic mistake. Parser must raise (non-UTF-8 bytes or no recognizable RIS structure), not hang or crash with a low-level decode trace. |
| `responses/openalex/*.json` | Real OpenAlex API responses captured 2026-04-28 (ticket 0006). Frozen test contract; replayed by `respx`. |
| `responses/crossref/*.json` | Real Crossref API responses captured 2026-04-28 (ticket 0006). Frozen test contract; replayed by `respx`. |

## Adding a fixture

1. Use the `bad-<descriptor>.ris` naming pattern for malformed inputs.
2. Add a row to the table above.
3. Reference the new fixture in the ticket whose tests need it
   (usually `0001-ris-roundtrip-and-config.erg`).
