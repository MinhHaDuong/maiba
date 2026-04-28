"""Metadata resolver protocol and result type."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
from hishel import FilterPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheClient

from maiba.model import Item


@dataclass
class ResolutionResult:
    candidate: Item
    confidence: float
    source: str


class MetadataResolver(Protocol):
    def resolve(self, item: Item) -> ResolutionResult | None: ...


def make_http_client(cfg_http, headers: dict[str, str], *, use_cache: bool = True) -> httpx.Client:
    """Build an HTTP client, optionally with caching via hishel.

    Uses FilterPolicy so responses are cached even when the upstream API
    does not send Cache-Control headers (OpenAlex and Crossref omit them).
    The storage default_ttl controls expiry instead.
    """
    if use_cache:
        cache_dir = Path(cfg_http.cache_dir).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        storage = SyncSqliteStorage(
            database_path=cache_dir / "http.db",
            default_ttl=cfg_http.cache_ttl_s,
        )
        return SyncCacheClient(
            storage=storage,
            policy=FilterPolicy(),
            headers=headers,
            timeout=cfg_http.timeout_s,
        )
    return httpx.Client(
        headers=headers,
        timeout=cfg_http.timeout_s,
    )
