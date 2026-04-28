"""Unit tests for the shared resolver scorer."""

from __future__ import annotations

from pathlib import Path

import pytest

from maiba.config import load_config
from maiba.model import Item
from maiba.resolvers._scoring import score_candidate

CFG = load_config(Path("config/maiba.yaml"))


def test_perfect_match_scores_high() -> None:
    inp = Item(TY="JOUR", TI="Engaging the public on CCS", AU=["Ashworth, Peta"], PY=2009)
    cand = Item(
        TY="JOUR",
        TI="Engaging the public on CCS",
        AU=["Ashworth, Peta", "Carr-Cornish, Simone"],
        PY=2009,
    )
    assert score_candidate(inp, cand, CFG) == pytest.approx(1.0)


def test_missing_input_authors_falls_back_to_title_only() -> None:
    """Items with empty/forbidden AU must still match on title alone."""
    inp = Item(
        TY="JOUR",
        TI="Incentivising CCS in the EU",
        AU=["et al."],
        PY=2010,
    )
    cand = Item(
        TY="JOUR",
        TI="Incentivising CCS in the EU",
        AU=["Boot-Handford, M.", "Abanades, J. C."],
        PY=2010,
    )
    score = score_candidate(inp, cand, CFG)
    assert score is not None
    assert score >= CFG.matching.title_similarity_min


def test_missing_input_authors_still_rejects_bad_title() -> None:
    """Title-only path is still bounded by title_min."""
    inp = Item(TY="JOUR", TI="Engaging the public on CCS", AU=[], PY=2009)
    cand = Item(
        TY="JOUR",
        TI="Carbon nanotubes for hydrogen storage",
        AU=["Different, A."],
        PY=2009,
    )
    assert score_candidate(inp, cand, CFG) is None


def test_empty_title_returns_none() -> None:
    """Cannot match on a missing title."""
    inp = Item(TY="JOUR", TI="", AU=["Ashworth, P."], PY=2009)
    cand = Item(TY="JOUR", TI="Anything", AU=["Ashworth, P."], PY=2009)
    assert score_candidate(inp, cand, CFG) is None


def test_low_overlap_is_rejected_when_authors_present() -> None:
    """When the input has authors, author overlap must clear the floor."""
    inp = Item(
        TY="JOUR",
        TI="Some Title About CCS",
        AU=["Smith, A.", "Jones, B."],
        PY=2020,
    )
    cand = Item(
        TY="JOUR",
        TI="Some Title About CCS",
        AU=["Doe, C.", "Roe, D."],
        PY=2020,
    )
    assert score_candidate(inp, cand, CFG) is None
