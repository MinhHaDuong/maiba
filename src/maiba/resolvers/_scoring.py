"""Shared candidate-scoring for resolvers.

Both `OpenAlexResolver` and `CrossrefResolver` route their search-path
candidates through `select_best_candidate`. The helper scores each
candidate, logs the input + top N at DEBUG, and returns the best
`ResolutionResult` (or None).

Title similarity is `max(token_sort_ratio, partial_ratio)` (ticket
0026): token_sort handles word reordering, partial_ratio handles
the case where the input title is a prefix or substring of a
longer candidate title (very common with Crossref-stored titles
like 'Allaying public concern… through the development of…').

Author axis is dropped when the input lacks usable authors — we
cannot penalise a candidate for failing to match what we never had
to compare against (ticket 0013).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

from maiba.config import Config
from maiba.model import Item

if TYPE_CHECKING:
    from maiba.resolvers import ResolutionResult

log = logging.getLogger("maiba.scoring")

_TOP_N = 3
_TITLE_TRUNCATE = 80


def _extract_lastname(name: str) -> str:
    """Return a normalized lowercase lastname from "Last, First" or "First Last"."""
    name = name.strip()
    if "," in name:
        return name.split(",")[0].strip().lower()
    parts = name.split()
    return parts[-1].lower() if parts else ""


def _first_lastname_display(authors: list[str]) -> str:
    """Return 'Lastname' or 'Lastname +N' for a compact author summary."""
    if not authors:
        return "—"
    first = _extract_lastname(authors[0]).capitalize() or authors[0]
    extra = len(authors) - 1
    return f"{first} +{extra}" if extra else first


def _truncate(s: str | None, n: int = _TITLE_TRUNCATE) -> str:
    if not s:
        return "''"
    if len(s) <= n:
        return repr(s)
    return repr(s[: n - 1] + "…")


def _title_sim(a: str, b: str) -> float:
    """max(token_sort, partial) / 100. Best of both metrics."""
    if not a or not b:
        return 0.0
    return max(fuzz.token_sort_ratio(a, b), fuzz.partial_ratio(a, b)) / 100.0


def _author_overlap(
    input_authors: list[str],
    candidate_authors: list[str],
    forbidden: list[str],
) -> float:
    """Fraction of input authors (excluding forbidden) found in candidates."""
    clean_input = [a for a in input_authors if a not in forbidden]
    if not clean_input:
        return 0.0

    input_lastnames = {_extract_lastname(a) for a in clean_input}
    candidate_lastnames = {_extract_lastname(a) for a in candidate_authors}

    if not input_lastnames:
        return 0.0

    matches = input_lastnames & candidate_lastnames
    return len(matches) / len(input_lastnames)


def score_candidate(input_item: Item, candidate: Item, cfg: Config) -> float | None:
    """Score a candidate against the input item.

    Returns confidence in [0, 1], or None if the candidate doesn't
    qualify (missing input title, sub-threshold title similarity, or
    sub-threshold author overlap when input has authors).
    """
    if not input_item.TI:
        return None

    title_sim = _title_sim(input_item.TI, candidate.TI or "")
    title_min = cfg.matching.title_similarity_min

    forbidden = cfg.gaps.forbidden_authors
    clean_au = [a for a in input_item.AU if a not in forbidden]

    if not clean_au:
        return title_sim if title_sim >= title_min else None

    overlap = _author_overlap(input_item.AU, candidate.AU, forbidden)
    confidence = title_sim * 0.7 + overlap * 0.3
    if confidence >= title_min and overlap >= cfg.matching.author_overlap_min:
        return confidence
    return None


def _raw_confidence(input_item: Item, candidate: Item, cfg: Config) -> float:
    """Confidence formula without the accept/reject gates — for ranking."""
    if not input_item.TI:
        return 0.0
    title_sim = _title_sim(input_item.TI, candidate.TI or "")
    forbidden = cfg.gaps.forbidden_authors
    clean_au = [a for a in input_item.AU if a not in forbidden]
    if not clean_au:
        return title_sim
    overlap = _author_overlap(input_item.AU, candidate.AU, forbidden)
    return title_sim * 0.7 + overlap * 0.3


def _log_top_candidates(input_item: Item, ranked: list[tuple[Item, float]]) -> None:
    """DEBUG-log the input record + top N candidates, one short line each."""
    if not log.isEnabledFor(logging.DEBUG):
        return
    log.debug(
        "INPUT  %s (PY=%s)  %s",
        input_item.id,
        input_item.PY,
        _truncate(input_item.TI),
    )
    for i, (cand, raw) in enumerate(ranked[:_TOP_N], 1):
        log.debug(
            "  top%d raw=%.2f  (%s, %s)  %s",
            i,
            raw,
            cand.PY if cand.PY is not None else "—",
            _first_lastname_display(list(cand.AU)),
            _truncate(cand.TI),
        )


def select_best_candidate(
    input_item: Item, candidates: list[Item], cfg: Config, source: str
) -> ResolutionResult | None:
    """Score candidates, log top N at DEBUG, return the best accepted result.

    "Best" here is the highest-scoring candidate that passes the
    accept/reject gates in `score_candidate`. Even rejected candidates
    are surfaced in the DEBUG log so a human can see why a record
    didn't match.
    """
    from maiba.resolvers import ResolutionResult

    ranked: list[tuple[Item, float]] = sorted(
        ((c, _raw_confidence(input_item, c, cfg)) for c in candidates),
        key=lambda t: t[1],
        reverse=True,
    )
    _log_top_candidates(input_item, ranked)

    for cand, _ in ranked:
        accepted = score_candidate(input_item, cand, cfg)
        if accepted is not None:
            return ResolutionResult(candidate=cand, confidence=accepted, source=source)
    return None
