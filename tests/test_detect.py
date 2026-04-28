"""Tests for gap detection."""

from pathlib import Path

from maiba.config import load_config
from maiba.detect import detect_gaps
from maiba.model import Item

CFG = load_config("config/maiba.yaml")


def test_complete_item_has_no_gaps():
    item = Item(TY="JOUR", TI="X", AU=["Doe, J."], PY=2020, DO="10.1/x", JO="Nature", AB="text")
    assert detect_gaps(item, CFG) == []


def test_missing_doi_is_not_a_default_gap():
    """DO is intentionally not in default recommended_fields — only the
    core trio (TI, AU, PY) is."""
    item = Item(TY="JOUR", TI="X", AU=["Doe, J."], PY=2020)
    assert "DO" not in detect_gaps(item, CFG)


def test_missing_doi_is_a_gap_when_user_adds_it():
    """Users can opt in to flagging missing DOIs by adding DO to
    recommended_fields in their config."""
    item = Item(TY="JOUR", TI="X", AU=["Doe, J."], PY=2020)
    cfg = load_config("config/maiba.yaml").model_copy(deep=True)
    cfg.gaps.recommended_fields = [*cfg.gaps.recommended_fields, "DO"]
    assert "DO" in detect_gaps(item, cfg)


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
    """With the default config (TI/AU/PY only), the gap count drops to the
    records that genuinely lack a core field — about 20: ~10 missing PY,
    plus ~6 'et al.' authors and a couple Anonymous."""
    from maiba.ris import read_ris

    items = list(read_ris(Path("tests/fixtures/ArchiveCCS.ris")))
    gapped = [it for it in items if detect_gaps(it, CFG)]
    assert 10 <= len(gapped) <= 30
