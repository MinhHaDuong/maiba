"""Unit tests for _merge_fix() in pipeline.py.

Ticket 0029: merge step should fill all empty fields from the resolver
candidate, not only those in the `gaps` list.

The merge contract (union form):
- For tags IN gaps:  overwrite if candidate has a filled value that differs
  (handles "et al." → real authors, stale data, etc.)
- For tags NOT IN gaps:  fill only empty slots (never overwrite the user's data)
"""

from pathlib import Path

from maiba.config import load_config
from maiba.model import Item
from maiba.pipeline import _merge_fix
from maiba.resolvers import ResolutionResult

CFG = load_config(Path("config/maiba.yaml"))


def test_merge_fills_missing_doi_even_if_not_in_gaps():
    """DOI returned by resolver must land in output even when DO
    wasn't in the gap set (e.g. user narrowed gap config to TI/AU/PY)."""
    item = Item(TY="JOUR", TI="x", AU=[], PY=2010, DO=None)
    candidate = Item(
        TY="JOUR",
        TI="x",
        AU=["Doe, J."],
        PY=2010,
        DO="10.1/x",
        JO="Energy Policy",
        VL="38",
    )
    result = ResolutionResult(candidate=candidate, confidence=0.9, source="crossref")
    fixed, applied = _merge_fix(item, result, gaps=["AU"], cfg=CFG, today="2026-04-28")
    assert fixed.AU == ["Doe, J."]  # asked-for field filled
    assert fixed.DO == "10.1/x"  # not asked-for, but came back — kept
    assert fixed.JO == "Energy Policy"  # same
    assert fixed.VL == "38"


def test_merge_does_not_overwrite_existing_fields():
    """If input already has a field set, the resolver's version doesn't overwrite."""
    item = Item(TY="JOUR", TI="My title", AU=["Smith, J."], PY=2010, DO="10.1/original")
    candidate = Item(TY="JOUR", TI="Different title", AU=["Doe, J."], PY=2010, DO="10.1/different")
    result = ResolutionResult(candidate=candidate, confidence=0.9, source="crossref")
    fixed, applied = _merge_fix(item, result, gaps=[], cfg=CFG, today="2026-04-28")
    assert fixed.TI == "My title"  # unchanged
    assert fixed.DO == "10.1/original"  # unchanged
    assert fixed.AU == ["Smith, J."]  # unchanged


def test_provenance_records_every_changed_field():
    """Provenance N1 notes must mention every field that was filled."""
    item = Item(TY="JOUR", TI="x", AU=[], PY=2010)
    candidate = Item(TY="JOUR", TI="x", AU=["Doe, J."], PY=2010, DO="10.1/x", JO="Energy Policy")
    result = ResolutionResult(candidate=candidate, confidence=0.9, source="crossref")
    fixed, applied = _merge_fix(item, result, gaps=["AU"], cfg=CFG, today="2026-04-28")
    n1_text = "\n".join(fixed.N1)
    assert "maiba:before AU=" in n1_text
    assert "maiba:before DO=" in n1_text
    assert "maiba:before JO=" in n1_text


def test_merge_overwrites_et_al_author_when_in_gaps():
    """Fields that are in `gaps` must be overwritten even if not empty.

    'et al.' is a filled-but-invalid author list. The gap detector puts AU
    in gaps for forbidden authors. The merge step must still replace it.
    """
    item = Item(TY="JOUR", TI="x", AU=["Ashworth, P.", "et al."], PY=2009)
    candidate = Item(TY="JOUR", TI="x", AU=["Ashworth, P.", "Carr-Cornish, S."], PY=2009)
    result = ResolutionResult(candidate=candidate, confidence=0.95, source="crossref")
    fixed, applied = _merge_fix(item, result, gaps=["AU"], cfg=CFG, today="2026-04-28")
    assert "Carr-Cornish, S." in fixed.AU
    assert "et al." not in fixed.AU
