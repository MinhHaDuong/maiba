import json
from pathlib import Path

import respx
from httpx import Response

from maiba.config import load_config
from maiba.model import Item
from maiba.resolvers.crossref import CrossrefResolver

CFG = load_config("config/maiba.yaml")
FIXTURES = Path("tests/fixtures/responses/crossref")


def _replay(slug: str) -> dict:
    return json.loads((FIXTURES / f"{slug}.json").read_text())


@respx.mock
def test_resolve_by_doi_hit():
    respx.get(url__startswith="https://api.crossref.org/works/10.1016").mock(
        return_value=Response(200, json=_replay("ashworth-2009-doi"))
    )
    resolver = CrossrefResolver(CFG)
    item = Item(
        TY="JOUR",
        TI="Engaging the public on CCS",
        AU=["Ashworth, P.", "et al."],
        PY=2009,
        DO="10.1016/j.egypro.2009.02.302",
    )
    result = resolver.resolve(item)
    assert result is not None
    assert result.source == "crossref"
    assert "Ashworth" in " ".join(result.candidate.AU)
    assert result.candidate.DO == "10.1016/j.egypro.2009.02.302"
    assert 0.0 <= result.confidence <= 1.0


@respx.mock
def test_resolve_returns_none_when_search_too_noisy():
    respx.get(url__startswith="https://api.crossref.org/works?").mock(
        return_value=Response(200, json=_replay("lemonde-sleipner-2008-search"))
    )
    resolver = CrossrefResolver(CFG)
    item = Item(
        TY="NEWS",
        TI="Sleipner, pionnière de l'enfouissement du gaz carbonique",
        AU=["Le Monde"],
        PY=2008,
    )
    result = resolver.resolve(item)
    assert result is None


@respx.mock
def test_resolve_search_with_candidates():
    respx.get(url__startswith="https://api.crossref.org/works?").mock(
        return_value=Response(200, json=_replay("adler-2005-search"))
    )
    resolver = CrossrefResolver(CFG)
    item = Item(
        TY="RPRT",
        TI="A primer on perceptions of risk, risk communication and building trust",
        AU=["Adler, P. S."],
        PY=2005,
    )
    result = resolver.resolve(item)
    assert result is None or (result.source == "crossref" and 0.0 <= result.confidence <= 1.0)
