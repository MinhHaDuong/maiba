from pathlib import Path

import pytest

from maiba.config import load_config
from maiba.model import Item
from maiba.pdf import PdfExtractionError, extract_first_page

CFG = load_config("config/maiba.yaml")
F = Path("tests/fixtures")


def test_extract_text_layer():
    item = Item(
        TY="JOUR", TI="x", AU=["a"], PY=2020, L1=[f"file://{F.absolute()}/sample-text.pdf"]
    )
    text = extract_first_page(item, CFG)
    assert text is not None and "Hello" in text


def test_no_l1_returns_none():
    item = Item(TY="JOUR", TI="x", AU=["a"], PY=2020, L1=[])
    assert extract_first_page(item, CFG) is None


def test_missing_file_raises():
    item = Item(TY="JOUR", TI="x", AU=["a"], PY=2020, L1=["file:///nonexistent/path.pdf"])
    with pytest.raises(PdfExtractionError):
        extract_first_page(item, CFG)


def test_corrupted_pdf_raises():
    item = Item(
        TY="JOUR", TI="x", AU=["a"], PY=2020, L1=[f"file://{F.absolute()}/sample-broken.pdf"]
    )
    with pytest.raises(PdfExtractionError):
        extract_first_page(item, CFG)


def test_non_file_url_skipped():
    item = Item(TY="JOUR", TI="x", AU=["a"], PY=2020, L1=["https://example.com/paper.pdf"])
    assert extract_first_page(item, CFG) is None
