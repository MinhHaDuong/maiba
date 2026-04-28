"""Metadata resolver protocol and result type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from maiba.model import Item


@dataclass
class ResolutionResult:
    candidate: Item
    confidence: float
    source: str


class MetadataResolver(Protocol):
    def resolve(self, item: Item) -> ResolutionResult | None: ...
