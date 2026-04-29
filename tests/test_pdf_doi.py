from pathlib import Path

import pytest

from maiba.config import load_config
from maiba.model import Item
from maiba.pdf import extract_doi_from_first_page

CFG = load_config("config/maiba.yaml")
F = Path(__file__).parent / "fixtures"


def test_doi_extracted_from_pdf_with_doi_in_first_page():
    """Fixture has 'doi: 10.1016/j.egypro.2009.02.302.' — trailing period stripped."""
    item = Item(
        TY="JOUR",
        TI="x",
        AU=["a"],
        PY=2009,
        L1=[f"file://{(F / 'sample-with-doi.pdf').absolute()}"],
    )
    doi = extract_doi_from_first_page(item, CFG)
    assert doi == "10.1016/j.egypro.2009.02.302"


def test_no_doi_in_first_page_returns_none():
    """sample-text.pdf has 'Hello fixture world' — no DOI pattern."""
    item = Item(
        TY="JOUR",
        TI="x",
        AU=["a"],
        PY=2020,
        L1=[f"file://{(F / 'sample-text.pdf').absolute()}"],
    )
    assert extract_doi_from_first_page(item, CFG) is None


def test_no_l1_returns_none():
    item = Item(TY="JOUR", TI="x", AU=["a"], PY=2020, L1=[])
    assert extract_doi_from_first_page(item, CFG) is None


def test_doi_trailing_punctuation_stripped():
    """The fixture DOI line ends with '.'; rstrip must remove it."""
    item = Item(
        TY="JOUR",
        TI="x",
        AU=["a"],
        PY=2009,
        L1=[f"file://{(F / 'sample-with-doi.pdf').absolute()}"],
    )
    doi = extract_doi_from_first_page(item, CFG)
    assert doi is not None and not doi.endswith((".", ",", ";", ":", ")"))


def test_corrupt_pdf_raises_extraction_error():
    """extract_doi_from_first_page propagates PdfExtractionError for corrupt PDFs."""
    from maiba.pdf import PdfExtractionError

    item = Item(
        TY="JOUR",
        TI="x",
        AU=["a"],
        PY=2020,
        L1=[f"file://{(F / 'sample-broken.pdf').absolute()}"],
    )
    with pytest.raises(PdfExtractionError):
        extract_doi_from_first_page(item, CFG)
