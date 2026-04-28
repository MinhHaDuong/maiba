"""Shared candidate-scoring for resolvers.

Both `OpenAlexResolver` and `CrossrefResolver` route their search-path
candidates through `score_candidate`. The function returns either a
confidence in [0, 1] or None if the candidate doesn't qualify.

The scoring drops the author axis when the input lacks authors — we
cannot penalise a candidate for failing to match what we never had to
compare against. This is the bug fix from ticket 0013.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from maiba.config import Config
from maiba.model import Item


def _extract_lastname(name: str) -> str:
    """Return a normalized lowercase lastname from "Last, First" or "First Last"."""
    name = name.strip()
    if "," in name:
        return name.split(",")[0].strip().lower()
    parts = name.split()
    return parts[-1].lower() if parts else ""


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

    title_sim = fuzz.token_sort_ratio(input_item.TI, candidate.TI or "") / 100.0
    title_min = cfg.matching.title_similarity_min

    forbidden = cfg.gaps.forbidden_authors
    clean_au = [a for a in input_item.AU if a not in forbidden]

    if not clean_au:
        # Title-only path: no author penalty when the input has nothing
        # comparable. Still bounded by title_min.
        return title_sim if title_sim >= title_min else None

    overlap = _author_overlap(input_item.AU, candidate.AU, forbidden)
    confidence = title_sim * 0.7 + overlap * 0.3
    if confidence >= title_min and overlap >= cfg.matching.author_overlap_min:
        return confidence
    return None
