"""Tests for PDF embedded metadata extraction."""

from pathlib import Path

import pytest

from maiba.config import load_config
from maiba.model import Item
from maiba.pdf import PdfMetadataError, extract_pdf_metadata

CFG = load_config(Path("config/maiba.yaml"))
F = Path(__file__).parent / "fixtures"


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


def test_info_dict_title_extracted(pdf_info_dict_path: Path) -> None:
    """PDF with /Title in info dict returns it under key 'title'."""
    meta = extract_pdf_metadata(make_item(pdf_info_dict_path), CFG)
    assert meta is not None
    assert meta["title"] == "MAIBA Info-Dict Test Title"


def test_xmp_title_extracted(pdf_xmp_path: Path) -> None:
    """PDF with XMP dc:title returns it under key 'title'."""
    meta = extract_pdf_metadata(make_item(pdf_xmp_path), CFG)
    assert meta is not None
    assert meta["title"] == "MAIBA XMP Test Title"


def test_xmp_author_extracted(pdf_xmp_path: Path) -> None:
    """PDF with XMP dc:creator returns it under key 'author'."""
    meta = extract_pdf_metadata(make_item(pdf_xmp_path), CFG)
    assert meta is not None
    assert meta["author"] == "xmp-test-author"


def test_result_is_dict_of_strings(pdf_info_dict_path: Path) -> None:
    """All values in the result dict are strings."""
    meta = extract_pdf_metadata(make_item(pdf_info_dict_path), CFG)
    assert meta is not None
    for k, v in meta.items():
        assert isinstance(k, str), f"Key {k!r} is not a string"
        assert isinstance(v, str), f"Value for {k!r} is not a string"
