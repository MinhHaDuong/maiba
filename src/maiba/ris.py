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
        yield _entry_to_item(entry)


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


def _item_to_entry(item: Item) -> dict:
    """Map an Item to a rispy-style dict.

    Field order matches what ArchiveCCS and most RIS exports emit
    (TY → AU → TI → PY → DA → JO → … → KW → L1 → N1) so a textual diff
    of input vs output highlights real fixes instead of reordering noise.
    """
    entry: dict = {"type_of_reference": item.TY}

    if item.AU:
        entry["authors"] = item.AU
    if item.TI:
        entry["title"] = item.TI
    if item.PY is not None:
        entry["year"] = str(item.PY)

    for item_field, rispy_key in _SCALAR_FIELDS:
        val = getattr(item, item_field)
        if val is not None:
            entry[rispy_key] = val

    if item.UR is not None:
        entry["urls"] = [item.UR]
    if item.KW:
        entry["keywords"] = item.KW
    if item.L1:
        entry["file_attachments1"] = item.L1
    if item.N1:
        entry["notes"] = item.N1

    return entry


def write_ris(items: Iterable[Item], path: Path) -> None:
    entries = [_item_to_entry(item) for item in items]
    writer = _MaibaWriter()
    text = writer.formats(entries)
    path.write_text(text, encoding="utf-8")
