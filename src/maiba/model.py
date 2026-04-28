"""Item data model — frozen contract from ARCHITECTURE.md §6."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from urllib.parse import unquote

from pydantic import BaseModel, field_validator, model_validator


class Item(BaseModel, frozen=True):
    """One bibliographic record. Field set is frozen per ARCHITECTURE.md §6.2."""

    id: str = ""
    TY: str
    TI: str = ""
    AU: list[str] = []
    PY: int | None = None
    DA: str | None = None
    JO: str | None = None
    T2: str | None = None
    VL: str | None = None
    IS: str | None = None
    SP: str | None = None
    EP: str | None = None
    DO: str | None = None
    UR: str | None = None
    LA: str | None = None
    KW: list[str] = []
    AB: str | None = None
    PB: str | None = None
    CY: str | None = None
    L1: list[str] = []
    N1: list[str] = []

    @field_validator("PY", mode="before")
    @classmethod
    def _parse_year(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            return int(v.strip().rstrip("/"))
        raise ValueError(f"cannot parse year: {v!r}")

    @model_validator(mode="after")
    def _derive_id(self) -> Item:
        if self.id:
            return self
        derived = _id_from_l1(self.L1) or _id_from_hash(self.TI, self.AU, self.PY)
        object.__setattr__(self, "id", derived)
        return self


def _id_from_l1(l1: list[str]) -> str:
    if not l1:
        return ""
    path = unquote(l1[0])
    return PurePosixPath(path).stem


def _id_from_hash(title: str, authors: list[str], year: int | None) -> str:
    key = f"{title}|{authors[0] if authors else ''}|{year}"
    return hashlib.sha1(key.encode()).hexdigest()
