"""Tests for gap detection."""

from pathlib import Path

from maiba.config import load_config
from maiba.detect import detect_gaps
from maiba.model import Item

CFG = load_config("config/maiba.yaml")


def test_complete_item_has_no_gaps():
    item = Item(TY="JOUR", TI="X", AU=["Doe, J."], PY=2020, DO="10.1/x", JO="Nature", AB="text")
    assert detect_gaps(item, CFG) == []


def test_missing_doi_is_recommended_gap():
    item = Item(TY="JOUR", TI="X", AU=["Doe, J."], PY=2020)
    assert "DO" in detect_gaps(item, CFG)


def test_missing_title_is_required_gap():
    item = Item(TY="JOUR", TI="", AU=["Doe, J."], PY=2020, DO="10.1/x")
    assert "TI" in detect_gaps(item, CFG)


def test_et_al_author_is_forbidden_gap():
    item = Item(TY="JOUR", TI="X", AU=["et al."], PY=2020, DO="10.1/x", JO="J", AB="a")
    assert "AU" in detect_gaps(item, CFG)


def test_anonymous_author_is_forbidden_gap():
    item = Item(TY="JOUR", TI="X", AU=["Anonymous"], PY=2020, DO="10.1/x", JO="J", AB="a")
    assert "AU" in detect_gaps(item, CFG)


def test_missing_year_is_required_gap():
    item = Item(TY="JOUR", TI="X", AU=["Doe, J."], DO="10.1/x")
    assert "PY" in detect_gaps(item, CFG)


def test_archiveccs_has_items_with_gaps():
    from maiba.ris import read_ris

    items = list(read_ris(Path("tests/fixtures/ArchiveCCS.ris")))
    gapped = [it for it in items if detect_gaps(it, CFG)]
    assert len(gapped) >= 30
