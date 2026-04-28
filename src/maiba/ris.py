"""RIS adapter over rispy — thin wrapper, not a parser."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from rispy.parser import LIST_TYPE_TAGS, RisParser
from rispy.writer import RisWriter

from maiba.model import Item

_TY_PATTERN = re.compile(r"^TY\s{1,2}- ", re.MULTILINE)

_SUBSTANTIVE_KEYS = frozenset(
    {
        "title",
        "year",
        "doi",
        "journal_name",
        "secondary_title",
        "volume",
        "number",
        "start_page",
        "end_page",
        "abstract",
        "publisher",
        "date",
        "language",
    }
)


class RisParseError(Exception):
    pass


class _MaibaParser(RisParser):
    DEFAULT_LIST_TAGS = LIST_TYPE_TAGS + ["L1"]


class _MaibaWriter(RisWriter):
    DEFAULT_LIST_TAGS = LIST_TYPE_TAGS + ["L1"]

    def set_header(self, count):
        return ""


def read_ris(path: Path) -> Iterator[Item]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RisParseError(f"binary file: {path}") from exc

    if not text.strip():
        return

    ty_count = len(_TY_PATTERN.findall(text))
    if ty_count == 0:
        raise RisParseError(f"no TY tags found: {path}")

    parser = _MaibaParser()
    entries = parser.parse(text)

    if ty_count > len(entries):
        raise RisParseError(
            f"truncated: {ty_count} TY tags but only {len(entries)} complete records in {path}"
        )

    for entry in entries:
        _validate_entry(entry, path)
        item = _entry_to_item(entry)
        _ORDER_CACHE[item.id] = list(entry.keys())
        yield item


def _validate_entry(entry: dict, path: Path) -> None:
    has_substantive = any(k in entry for k in _SUBSTANTIVE_KEYS)
    if not has_substantive:
        raise RisParseError(f"record has no substantive fields in {path}")


def _entry_to_item(entry: dict) -> Item:
    year_raw = entry.get("year")
    urls = entry.get("urls", [])

    return Item(
        TY=entry.get("type_of_reference", ""),
        TI=entry.get("title", ""),
        AU=entry.get("authors", []),
        PY=year_raw,
        DA=entry.get("date"),
        JO=entry.get("journal_name"),
        T2=entry.get("secondary_title"),
        VL=entry.get("volume"),
        IS=entry.get("number"),
        SP=entry.get("start_page"),
        EP=entry.get("end_page"),
        DO=entry.get("doi"),
        UR=urls[0] if urls else None,
        LA=entry.get("language"),
        KW=entry.get("keywords", []),
        AB=entry.get("abstract"),
        PB=entry.get("publisher"),
        CY=entry.get("place_published"),
        L1=entry.get("file_attachments1", []),
        N1=entry.get("notes", []),
    )


_SCALAR_FIELDS: list[tuple[str, str]] = [
    ("DA", "date"),
    ("JO", "journal_name"),
    ("T2", "secondary_title"),
    ("VL", "volume"),
    ("IS", "number"),
    ("SP", "start_page"),
    ("EP", "end_page"),
    ("DO", "doi"),
    ("LA", "language"),
    ("AB", "abstract"),
    ("PB", "publisher"),
    ("CY", "place_published"),
]

_DEFAULT_KEY_ORDER: list[str] = [
    "type_of_reference",
    "authors",
    "title",
    "year",
    "date",
    "journal_name",
    "secondary_title",
    "volume",
    "number",
    "start_page",
    "end_page",
    "doi",
    "language",
    "abstract",
    "publisher",
    "place_published",
    "urls",
    "keywords",
    "file_attachments1",
    "notes",
]

_ORDER_CACHE: dict[str, list[str]] = {}


def _populate_entry(item: Item) -> dict:
    populated: dict = {"type_of_reference": item.TY}
    if item.AU:
        populated["authors"] = item.AU
    if item.TI:
        populated["title"] = item.TI
    if item.PY is not None:
        populated["year"] = str(item.PY)
    for item_field, rispy_key in _SCALAR_FIELDS:
        val = getattr(item, item_field)
        if val is not None:
            populated[rispy_key] = val
    if item.UR is not None:
        populated["urls"] = [item.UR]
    if item.KW:
        populated["keywords"] = item.KW
    if item.L1:
        populated["file_attachments1"] = item.L1
    if item.N1:
        populated["notes"] = item.N1
    return populated


def _item_to_entry(item: Item) -> dict:
    """Map an Item to a rispy-style dict.

    Preserves the input key order from `read_ris` (cached by item.id) so
    that round-tripping a file through `read → write` is textually stable
    and a diff highlights real fixes instead of reordering noise. New
    keys (added by the pipeline, e.g. `notes` provenance) are appended in
    canonical order after the cached ones. Items with no cached order
    fall back to the canonical order entirely.
    """
    populated = _populate_entry(item)
    cached_order = _ORDER_CACHE.get(item.id, [])
    ordered: dict = {}
    for key in cached_order:
        if key in populated:
            ordered[key] = populated[key]
    for key in _DEFAULT_KEY_ORDER:
        if key in populated and key not in ordered:
            ordered[key] = populated[key]
    return ordered


def write_ris(items: Iterable[Item], path: Path) -> None:
    entries = [_item_to_entry(item) for item in items]
    writer = _MaibaWriter()
    text = writer.formats(entries)
    path.write_text(text, encoding="utf-8")
