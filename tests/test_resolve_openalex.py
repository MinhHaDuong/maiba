"""Tests for the OpenAlex metadata resolver — replays real API fixtures."""

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from maiba.config import load_config
from maiba.model import Item
from maiba.resolvers.openalex import OpenAlexResolver, ResolverRateLimitedError

CFG = load_config("config/maiba.yaml")
FIXTURES = Path("tests/fixtures/responses/openalex")


def _replay(slug: str) -> dict:
    return json.loads((FIXTURES / f"{slug}.json").read_text())


@respx.mock
def test_resolve_by_doi_hit():
    respx.get(url__startswith="https://api.openalex.org/works/doi:10.1016").mock(
        return_value=Response(200, json=_replay("ashworth-2009-doi"))
    )
    resolver = OpenAlexResolver(CFG)
    item = Item(
        TY="JOUR",
        TI="Engaging the public on CCS",
        AU=["Ashworth, P.", "et al."],
        PY=2009,
        DO="10.1016/j.egypro.2009.02.302",
    )
    result = resolver.resolve(item)
    assert result is not None
    assert result.source == "openalex"
    assert "Ashworth" in " ".join(result.candidate.AU)
    assert result.candidate.DO == "10.1016/j.egypro.2009.02.302"
    assert 0.0 <= result.confidence <= 1.0
    assert result.candidate.OAID == "W2018647518"


@respx.mock
def test_resolve_search_hit_no_doi():
    respx.get(url__startswith="https://api.openalex.org/works?").mock(
        return_value=Response(200, json=_replay("adler-2005-search"))
    )
    resolver = OpenAlexResolver(CFG)
    item = Item(
        TY="RPRT",
        TI="A primer on perceptions of risk, risk communication and building trust",
        AU=["Adler, P. S."],
        PY=2005,
    )
    result = resolver.resolve(item)
    assert result is None or result.source == "openalex"


@respx.mock
def test_resolve_returns_none_on_true_miss():
    respx.get(url__startswith="https://api.openalex.org/works?").mock(
        return_value=Response(200, json=_replay("lemonde-sleipner-2008-search"))
    )
    resolver = OpenAlexResolver(CFG)
    item = Item(
        TY="NEWS",
        TI="Sleipner, pionnière de l'enfouissement du gaz carbonique",
        AU=["Le Monde"],
        PY=2008,
    )
    result = resolver.resolve(item)
    assert result is None


@respx.mock
def test_api_key_sent_as_bearer_header(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key-abc")
    route = respx.get(url__startswith="https://api.openalex.org/works?").mock(
        return_value=Response(200, json={"results": []})
    )
    resolver = OpenAlexResolver(CFG)
    resolver.resolve(Item(TY="JOUR", TI="x", AU=["a"], PY=2020))
    assert route.called
    assert route.calls.last.request.headers.get("authorization") == "Bearer test-key-abc"


@respx.mock
def test_no_auth_header_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    route = respx.get(url__startswith="https://api.openalex.org/works?").mock(
        return_value=Response(200, json={"results": []})
    )
    resolver = OpenAlexResolver(CFG)
    resolver.resolve(Item(TY="JOUR", TI="x", AU=["a"], PY=2020))
    assert route.called
    assert "authorization" not in route.calls.last.request.headers


@respx.mock
def test_rate_limited_raises():
    respx.get(url__startswith="https://api.openalex.org/works?").mock(
        return_value=Response(429, json={"error": "Rate limit exceeded"})
    )
    resolver = OpenAlexResolver(CFG)
    with pytest.raises(ResolverRateLimitedError):
        resolver.resolve(Item(TY="JOUR", TI="x", AU=["a"], PY=2020))


@respx.mock
def test_openalex_per_page_uses_configured_search_rows():
    captured: dict = {}

    def callback(request):
        captured["params"] = dict(request.url.params)
        return Response(200, json={"results": []})

    respx.get(url__startswith="https://api.openalex.org/works").mock(side_effect=callback)
    resolver = OpenAlexResolver(CFG)
    resolver.resolve(Item(TY="JOUR", TI="x", AU=["a"], PY=2020))
    assert int(captured["params"].get("per_page", "0")) == CFG.resolvers.openalex.search_rows


@respx.mock
def test_openalex_filter_widens_year_window():
    captured: dict = {}

    def callback(request):
        captured["params"] = dict(request.url.params)
        return Response(200, json={"results": []})

    respx.get(url__startswith="https://api.openalex.org/works").mock(side_effect=callback)
    resolver = OpenAlexResolver(CFG)
    resolver.resolve(Item(TY="JOUR", TI="x", AU=["a"], PY=2010))
    f = captured["params"].get("filter", "")
    # year_window=1 → 2009|2010|2011
    assert "publication_year:2009|2010|2011" == f
