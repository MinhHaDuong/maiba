"""Pipeline: read RIS → detect gaps → resolve → merge with provenance → write."""

from __future__ import annotations

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
from maiba.resolvers.openalex import OpenAlexResolver
from maiba.ris import read_ris, write_ris

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


@dataclass
class FixApplied:
    item_id: str
    source: str
    confidence: float
    fields_changed: dict[str, tuple[Any, Any]]


@dataclass
class Report:
    scanned: int = 0
    with_gaps: int = 0
    fixed: int = 0
    skipped_below_threshold: int = 0
    fixes: list[FixApplied] = field(default_factory=list)


def run(
    input: Path,
    output: Path | None,
    cfg: Config,
    apply: bool,
    quiet: bool = False,
    use_cache: bool = True,
) -> Report:
    items = list(read_ris(input))
    resolvers = _build_resolvers(cfg, use_cache=use_cache)
    today = date.today().isoformat()
    report = Report(scanned=len(items))
    out_items: list[Item] = []
    emitted = False

    try:
        for item in items:
            gaps = detect_gaps(item, cfg)
            if not gaps:
                out_items.append(item)
                _emit_progress(_classify(0, 0), quiet=quiet)
                emitted = True
                continue
            report.with_gaps += 1

            result = _try_resolvers(item, resolvers)
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
            _emit_progress(_classify(len(gaps), len(fix.fields_changed)), quiet=quiet)
            emitted = True
    finally:
        if emitted and not quiet and sys.stderr.isatty():
            print("", file=sys.stderr, flush=True)

    if apply and output is not None:
        write_ris(out_items, output)

    return report


def _build_resolvers(cfg: Config, *, use_cache: bool = True) -> list[MetadataResolver]:
    return [_RESOLVER_BUILDERS[name](cfg, use_cache=use_cache) for name in cfg.resolvers.order]


def _try_resolvers(item: Item, resolvers: list[MetadataResolver]) -> ResolutionResult | None:
    for resolver in resolvers:
        result = resolver.resolve(item)
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
