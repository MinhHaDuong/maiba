"""Tests for PDF embedded metadata extraction."""

from pathlib import Path

import pytest

from maiba.config import load_config
from maiba.model import Item
from maiba.pdf import PdfMetadataError, extract_pdf_metadata

CFG = load_config(Path("config/maiba.yaml"))
F = Path(__file__).parent / "fixtures"

# Real corpus PDF with XMP dc_title and dc_creator
XMP_PDF = (
    F
    / "ArchiveCCS-cleaned/files/37295"
    / "Bataille.ea-2006-RapportSurLesNouvellesTechnologiesDeLEnergieEtLaSéquestrationDuCO2.pdf"
)

# Real corpus PDF with info-dict title (no XMP or minimal XMP)
INFO_PDF = (
    F
    / "ArchiveCCS-cleaned/files/37267"
    / "Adler.ea-2005-PrimerOnPerceptionsOfRiskCommunicationAndBuildingTrust.pdf"
)


def make_item(path: Path) -> Item:
    return Item(
        TY="JOUR",
        TI="x",
        AU=["a"],
        PY=2020,
        L1=[f"file://{path.absolute()}"],
    )


def test_no_l1_returns_none() -> None:
    item = Item(TY="JOUR", TI="x", AU=["a"], PY=2020, L1=[])
    assert extract_pdf_metadata(item, CFG) is None


def test_pdf_with_no_metadata_returns_empty_dict() -> None:
    """A PDF with empty info dict and no XMP returns {}, not None."""
    item = make_item(F / "sample-no-metadata.pdf")
    result = extract_pdf_metadata(item, CFG)
    assert result == {}


def test_missing_file_raises() -> None:
    item = Item(
        TY="JOUR",
        TI="x",
        AU=["a"],
        PY=2020,
        L1=["file:///nonexistent/path/to.pdf"],
    )
    with pytest.raises(PdfMetadataError):
        extract_pdf_metadata(item, CFG)


def test_corrupted_pdf_raises() -> None:
    item = make_item(F / "sample-broken.pdf")
    with pytest.raises(PdfMetadataError):
        extract_pdf_metadata(item, CFG)


def test_info_dict_title_extracted() -> None:
    """PDF with /Title in info dict returns it under key 'title'."""
    meta = extract_pdf_metadata(make_item(INFO_PDF), CFG)
    assert meta is not None
    assert "title" in meta
    # The known title from the info dict spike
    assert "TKC Risk Paper" in meta["title"]


def test_xmp_title_extracted() -> None:
    """PDF with XMP dc:title returns it under key 'title'."""
    meta = extract_pdf_metadata(make_item(XMP_PDF), CFG)
    assert meta is not None
    assert "title" in meta
    # Known value from the dc_title spike: {'x-default': 'Microsoft Word - i2965.doc'}
    assert "i2965" in meta["title"]


def test_xmp_author_extracted() -> None:
    """PDF with XMP dc:creator returns it under key 'author'."""
    meta = extract_pdf_metadata(make_item(XMP_PDF), CFG)
    assert meta is not None
    assert "author" in meta
    # Known value from spike: ['ddesmicht']
    assert "ddesmicht" in meta["author"]


def test_result_is_dict_of_strings() -> None:
    """All values in the result dict are strings."""
    meta = extract_pdf_metadata(make_item(INFO_PDF), CFG)
    assert meta is not None
    for k, v in meta.items():
        assert isinstance(k, str), f"Key {k!r} is not a string"
        assert isinstance(v, str), f"Value for {k!r} is not a string"
