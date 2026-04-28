"""Tests for HTTP response caching via hishel."""

import respx
from httpx import Response

from maiba.config import load_config
from maiba.model import Item
from maiba.resolvers.openalex import OpenAlexResolver


@respx.mock
def test_resolver_uses_cache_on_second_call(tmp_path):
    cfg = load_config("config/maiba.yaml")
    cfg.http.cache_dir = str(tmp_path / "cache")

    route = respx.get(url__regex=r".*api\.openalex\.org/works/doi:.*").mock(
        return_value=Response(
            200,
            headers={"cache-control": "max-age=86400"},
            json={
                "title": "X",
                "publication_year": 2020,
                "authorships": [],
                "doi": "https://doi.org/10.1/x",
            },
        )
    )
    resolver = OpenAlexResolver(cfg)
    item = Item(TY="JOUR", TI="X", DO="10.1/x")

    resolver.resolve(item)
    resolver.resolve(item)

    assert route.call_count == 1, "second call should be served from cache"


@respx.mock
def test_no_cache_flag_bypasses_cache(tmp_path):
    cfg = load_config("config/maiba.yaml")
    cfg.http.cache_dir = str(tmp_path / "cache")

    route = respx.get(url__regex=r".*api\.openalex\.org/works/doi:.*").mock(
        return_value=Response(
            200,
            json={
                "title": "X",
                "publication_year": 2020,
                "authorships": [],
                "doi": "https://doi.org/10.1/x",
            },
        )
    )
    resolver = OpenAlexResolver(cfg, use_cache=False)
    item = Item(TY="JOUR", TI="X", DO="10.1/x")

    resolver.resolve(item)
    resolver.resolve(item)

    assert route.call_count == 2, "no-cache mode should hit the network every time"
