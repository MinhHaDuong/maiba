"""Pipeline: read RIS → detect gaps → resolve → merge with provenance → write."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from maiba.config import Config
from maiba.detect import detect_gaps
from maiba.model import Item
from maiba.resolvers import MetadataResolver, ResolutionResult
from maiba.resolvers.crossref import CrossrefResolver
from maiba.resolvers.openalex import OpenAlexResolver, ResolverRateLimitedError
from maiba.ris import read_ris, write_ris

log = logging.getLogger("maiba.pipeline")

_RESOLVER_BUILDERS = {
    "openalex": OpenAlexResolver,
    "crossref": CrossrefResolver,
}

GLYPH_SKIP = "."
GLYPH_NOT_FIXED = "0"
GLYPH_FULL_FIX = "*"
GLYPH_PARTIAL_FIX = "+"


def _classify(gaps_count: int, fields_changed_count: int) -> str:
    if gaps_count == 0:
        return GLYPH_SKIP
    if fields_changed_count == 0:
        return GLYPH_NOT_FIXED
    if fields_changed_count >= gaps_count:
        return GLYPH_FULL_FIX
    return GLYPH_PARTIAL_FIX


def _emit_progress(char: str, *, quiet: bool = False) -> None:
    if quiet or not sys.stderr.isatty():
        return
    print(char, end="", flush=True, file=sys.stderr)


def _preview_counts(items: list[Item], cfg: Config) -> tuple[int, int, int]:
    """Classify each item by what the pipeline will do with it.

    Returns (n_skip, n_doi_lookup, n_title_search).
    """
    n_skip = 0
    n_doi_lookup = 0
    n_title_search = 0
    for it in items:
        if not detect_gaps(it, cfg):
            n_skip += 1
        elif it.DO:
            n_doi_lookup += 1
        else:
            n_title_search += 1
    return n_skip, n_doi_lookup, n_title_search


def _announce(
    total: int,
    n_skip: int,
    n_doi_lookup: int,
    n_title_search: int,
    *,
    quiet: bool = False,
) -> None:
    if quiet or not sys.stderr.isatty() or total == 0:
        return
    print(
        f"Scanning {total} records "
        f"({n_skip} complete, {n_doi_lookup} DOI lookups, {n_title_search} title searches)…",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"Legend: {GLYPH_SKIP} no gaps  "
        f"{GLYPH_NOT_FIXED} not fixed  "
        f"{GLYPH_PARTIAL_FIX} partial fix  "
        f"{GLYPH_FULL_FIX} full fix",
        file=sys.stderr,
        flush=True,
    )


@dataclass
class FixApplied:
    item_id: str
    source: str
    confidence: float
    fields_changed: dict[str, tuple[Any, Any]]


@dataclass
class Report:
    """Aggregate result of a `run()`.

    `rate_limited` counts records that ran with a degraded resolver
    chain (at least one resolver was skipped because it was rate
    limited earlier in this run). Records before the first 429 are
    not counted.
    """

    scanned: int = 0
    with_gaps: int = 0
    fixed: int = 0
    skipped_below_threshold: int = 0
    rate_limited: int = 0
    fixes: list[FixApplied] = field(default_factory=list)


def run(  # noqa: PLR0915
    input: Path,
    output: Path | None,
    cfg: Config,
    quiet: bool = False,
    use_cache: bool = False,
) -> Report:
    items = list(read_ris(input))
    log.info("scanning %d records from %s", len(items), input)
    resolvers = _build_resolvers(cfg, use_cache=use_cache)
    today = date.today().isoformat()
    report = Report(scanned=len(items))
    out_items: list[Item] = []
    emitted = False

    _announce(len(items), *_preview_counts(items, cfg), quiet=quiet)

    dead_resolvers: set[str] = set()
    try:
        for item in items:
            gaps = detect_gaps(item, cfg)
            if not gaps:
                out_items.append(item)
                _emit_progress(_classify(0, 0), quiet=quiet)
                emitted = True
                continue
            report.with_gaps += 1

            result = _try_resolvers(item, resolvers, dead_resolvers)
            if dead_resolvers:
                report.rate_limited += 1
            if result is None:
                out_items.append(item)
                _emit_progress(_classify(len(gaps), 0), quiet=quiet)
                emitted = True
                continue
            if result.confidence < cfg.matching.apply_threshold:
                report.skipped_below_threshold += 1
                out_items.append(item)
                _emit_progress(_classify(len(gaps), 0), quiet=quiet)
                emitted = True
                continue

            fixed_item, fix = _merge_fix(item, result, gaps, cfg, today)
            out_items.append(fixed_item)
            if fix.fields_changed:
                report.fixed += 1
                report.fixes.append(fix)
                log.info(
                    "fixed %s via %s (conf=%.2f, fields=%s)",
                    fix.item_id,
                    fix.source,
                    fix.confidence,
                    sorted(fix.fields_changed.keys()),
                )
            log.debug(
                "record %s gaps=%s fields_changed=%s", item.id, gaps, list(fix.fields_changed)
            )
            _emit_progress(_classify(len(gaps), len(fix.fields_changed)), quiet=quiet)
            emitted = True
    finally:
        if emitted and not quiet and sys.stderr.isatty():
            print("", file=sys.stderr, flush=True)

    if output is not None:
        write_ris(out_items, output)

    return report


def _build_resolvers(cfg: Config, *, use_cache: bool = False) -> list[MetadataResolver]:
    return [_RESOLVER_BUILDERS[name](cfg, use_cache=use_cache) for name in cfg.resolvers.order]


def _try_resolvers(
    item: Item,
    resolvers: list[MetadataResolver],
    dead: set[str],
) -> ResolutionResult | None:
    """Iterate resolvers, skipping any in `dead`.

    On `ResolverRateLimitedError` from a resolver call, the resolver's
    `source` is added to `dead` (so subsequent records skip it) and the
    next resolver in the chain is tried for THIS record. The first
    failure of a given resolver is logged at WARNING.
    """
    for resolver in resolvers:
        source = getattr(resolver, "source", resolver.__class__.__name__.lower())
        if source in dead:
            continue
        try:
            result = resolver.resolve(item)
        except ResolverRateLimitedError as exc:
            log.warning("%s: rate limited — skipping for the rest of this run", exc.source)
            dead.add(exc.source)
            continue
        if result is not None:
            return result
    return None


def _merge_fix(
    item: Item, result: ResolutionResult, gaps: list[str], cfg: Config, today: str
) -> tuple[Item, FixApplied]:
    candidate = result.candidate
    new_data = item.model_dump()
    fields_changed: dict[str, tuple[Any, Any]] = {}

    for tag in gaps:
        new_value = getattr(candidate, tag, None)
        old_value = getattr(item, tag, None)
        if _is_filled(new_value) and new_value != old_value:
            new_data[tag] = new_value
            fields_changed[tag] = (old_value, new_value)

    if not fields_changed:
        return item, FixApplied(
            item_id=item.id, source=result.source, confidence=result.confidence, fields_changed={}
        )

    prefix = cfg.provenance.tag_prefix
    n1 = list(item.N1)
    n1.append(
        f"{prefix}:autofixed:{today} source={result.source} confidence={result.confidence:.2f}"
    )
    for field_name, (before, _after) in fields_changed.items():
        n1.append(f"{prefix}:before {field_name}={before}")
    new_data["N1"] = n1
    new_data["id"] = item.id

    fixed = Item(**new_data)
    return fixed, FixApplied(
        item_id=item.id,
        source=result.source,
        confidence=result.confidence,
        fields_changed=fields_changed,
    )


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True
