"""Gap detection for bibliographic items."""

from __future__ import annotations

from maiba.config import Config
from maiba.model import Item


def detect_gaps(item: Item, cfg: Config) -> list[str]:
    """Return RIS tags that are missing or invalid for the given item."""
    gaps: list[str] = []
    seen: set[str] = set()

    for tag in (*cfg.gaps.required_fields, *cfg.gaps.recommended_fields):
        if tag in seen:
            continue
        val = getattr(item, tag, None)
        if val is None or val == "" or val == []:
            gaps.append(tag)
            seen.add(tag)

    if item.AU and "AU" not in seen:
        for forbidden in cfg.gaps.forbidden_authors:
            if any(forbidden.lower() in au.lower() for au in item.AU):
                gaps.append("AU")
                break

    return gaps
