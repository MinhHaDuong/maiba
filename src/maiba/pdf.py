"""PDF text extraction utilities."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import pypdf
import pypdf.errors

from maiba.config import Config
from maiba.model import Item

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be read (missing file or corrupt content)."""


def _resolve_l1_path(l1: list[str]) -> Path | None:
    """Return the first file:// URL in l1 as a Path, or None."""
    for url in l1:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return Path(unquote(parsed.path))
    return None


class PdfMetadataError(Exception):
    """Raised on corrupt PDF or unreadable metadata structure."""


_INFO_KEY_MAP: list[tuple[str, str]] = [
    ("/Title", "title"),
    ("/Author", "author"),
    ("/Subject", "subject"),
    ("/Keywords", "keywords"),
    ("/Creator", "creator"),
    ("/Producer", "producer"),
    ("/CreationDate", "creation_date"),
    ("/ModDate", "mod_date"),
]

_XMP_ATTR_MAP: list[tuple[str, str]] = [
    ("dc_title", "title"),
    ("dc_creator", "author"),
    ("dc_subject", "subject"),
    ("dc_description", "subject"),
    ("dc_language", "language"),
]


def _xmp_scalar(val: object) -> str | None:
    """Normalize an XMP value (LangAlt dict or seq list) to a plain string."""
    if isinstance(val, dict):
        return val.get("x-default") or next(iter(val.values()), None)
    if isinstance(val, list):
        return next((str(v) for v in val if v), None)
    return str(val) if val else None


def _extract_info_dict(info: object) -> dict[str, str]:
    result: dict[str, str] = {}
    for src_key, out_key in _INFO_KEY_MAP:
        val = info.get(src_key)  # type: ignore[union-attr]
        if val:
            result[out_key] = str(val)
    return result


def _extract_xmp_meta(xmp: object) -> dict[str, str]:
    result: dict[str, str] = {}
    for xmp_attr, out_key in _XMP_ATTR_MAP:
        try:
            raw = getattr(xmp, xmp_attr, None)
        except AttributeError:
            continue
        val = _xmp_scalar(raw)
        if val:
            result[out_key] = val
    return result


def extract_pdf_metadata(item: Item, cfg: Config) -> dict[str, str] | None:
    """Return normalized metadata dict from the Item's L1 PDF, or None if no L1.

    Keys (when present): title, author, subject, keywords, creator, producer,
    creation_date, mod_date.

    Returns {} if the PDF opens fine but has no metadata.
    Raises PdfMetadataError on missing file or corrupt PDF.

    cfg is reserved for future options.
    """
    path = _resolve_l1_path(item.L1)
    if path is None:
        return None
    if not path.exists():
        raise PdfMetadataError(f"File not found: {path}")
    try:
        reader = pypdf.PdfReader(str(path))
    except pypdf.errors.PdfReadError as exc:
        raise PdfMetadataError(f"Cannot read PDF: {path}") from exc

    result = _extract_info_dict(reader.metadata) if reader.metadata else {}
    try:
        if reader.xmp_metadata:
            result.update(_extract_xmp_meta(reader.xmp_metadata))
    except pypdf.errors.PdfReadError:
        pass
    return result


def extract_first_page(item: Item, cfg: Config) -> str | None:
    """Return first-page text from the Item's L1 PDF, or None if unavailable.

    Returns None if the item has no L1 links or none are file:// URLs.
    Raises PdfExtractionError if the file is missing or the PDF is corrupt.

    cfg is reserved for future encoding/timeout options.
    """
    path = _resolve_l1_path(item.L1)
    if path is None:
        return None
    if not path.exists():
        raise PdfExtractionError(f"File not found: {path}")
    try:
        reader = pypdf.PdfReader(str(path))
        return reader.pages[0].extract_text()
    except pypdf.errors.PdfReadError as exc:
        raise PdfExtractionError(f"Cannot read PDF: {path}") from exc


def extract_doi_from_first_page(item: Item, cfg: Config) -> str | None:
    """Return the first DOI found in the PDF first-page text, or None.

    Returns None if the item has no L1 links, or no DOI pattern is found.
    Raises PdfExtractionError if the file is missing or the PDF is corrupt
    (propagated from extract_first_page — callers should catch it).

    Trailing punctuation (.,;:)) is stripped: DOIs in prose like
    "(doi:10.x/y)" or "...see doi:10.x/y." capture the delimiter.
    """
    text = extract_first_page(item, cfg)
    if not text:
        return None
    m = DOI_RE.search(text)
    return m.group(0).rstrip(".,;:)") if m else None
