"""PDF text extraction utilities."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

import pypdf
import pypdf.errors

from maiba.config import Config
from maiba.model import Item


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be read (missing file or corrupt content)."""


def _resolve_l1_path(l1: list[str]) -> Path | None:
    """Return the first file:// URL in l1 as a Path, or None."""
    for url in l1:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return Path(unquote(parsed.path))
    return None


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
