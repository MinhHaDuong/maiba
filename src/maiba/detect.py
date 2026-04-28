"""Gap detection for bibliographic items."""

from __future__ import annotations

from maiba.config import Config
from maiba.model import Item


def detect_gaps(item: Item, cfg: Config) -> list[str]:
    """Return RIS tags that are missing or invalid for the given item."""
    gaps: list[str] = []

    for tag in cfg.gaps.required_fields:
        val = getattr(item, tag, None)
        if val is None or val == "" or val == []:
            gaps.append(tag)

    for tag in cfg.gaps.recommended_fields:
        val = getattr(item, tag, None)
        if val is None or val == "" or val == []:
            gaps.append(tag)

    if item.AU:
        for forbidden in cfg.gaps.forbidden_authors:
            if any(forbidden.lower() in au.lower() for au in item.AU):
                if "AU" not in gaps:
                    gaps.append("AU")

    return gaps
