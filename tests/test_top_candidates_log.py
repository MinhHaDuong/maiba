"""DEBUG output shape: input + top-3 candidates per resolver call."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import respx
from httpx import Response

from maiba.config import load_config
from maiba.model import Item
from maiba.resolvers.crossref import CrossrefResolver

CONFIG = Path(__file__).resolve().parent.parent / "config" / "maiba.yaml"


@respx.mock
def test_select_best_candidate_logs_input_and_top3(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A search call emits exactly one 'input id=' line and three 'topN ' lines."""
    fake_items = [
        {
            "DOI": f"10.1/x{i}",
            "title": [f"unrelated candidate {i}"],
            "author": [{"family": f"Other{i}", "given": "A."}],
            "issued": {"date-parts": [[2020]]},
            "type": "journal-article",
        }
        for i in range(5)
    ]
    respx.get(url__startswith="https://api.crossref.org/works").mock(
        return_value=Response(200, json={"message": {"items": fake_items}})
    )

    resolver = CrossrefResolver(load_config(CONFIG))
    item = Item(TY="JOUR", TI="A unique input title for testing", AU=[], PY=2020)

    with caplog.at_level(logging.DEBUG, logger="maiba.scoring"):
        resolver.resolve(item)

    messages = [r.getMessage() for r in caplog.records if r.name == "maiba.scoring"]
    inputs = [m for m in messages if m.startswith("INPUT  ")]
    tops = [m for m in messages if m.lstrip().startswith("top")]
    assert len(inputs) == 1, f"expected 1 INPUT log line, got {len(inputs)}: {messages}"
    assert sum(1 for m in tops if "top1 " in m) == 1
    assert sum(1 for m in tops if "top2 " in m) == 1
    assert sum(1 for m in tops if "top3 " in m) == 1
    assert sum(1 for m in tops if "top4 " in m) == 0, "top-N is capped at 3"


@respx.mock
def test_winner_is_marked_with_asterisk(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The accepted candidate's DEBUG line carries '*' as marker; others do not."""
    # one good candidate (matching title + author), several decoys
    items = [
        {
            "DOI": "10.1/decoy",
            "title": ["Totally unrelated decoy paper"],
            "author": [{"family": "NoMatch", "given": "X."}],
            "issued": {"date-parts": [[2020]]},
            "type": "journal-article",
        },
        {
            "DOI": "10.1/winner",
            "title": ["A unique input title for testing exactly"],
            "author": [{"family": "Smith", "given": "John"}],
            "issued": {"date-parts": [[2020]]},
            "type": "journal-article",
        },
        {
            "DOI": "10.1/decoy2",
            "title": ["Another decoy"],
            "author": [{"family": "NoMatch", "given": "Y."}],
            "issued": {"date-parts": [[2020]]},
            "type": "journal-article",
        },
    ]
    respx.get(url__startswith="https://api.crossref.org/works").mock(
        return_value=Response(200, json={"message": {"items": items}})
    )

    resolver = CrossrefResolver(load_config(CONFIG))
    item = Item(
        TY="JOUR",
        TI="A unique input title for testing exactly",
        AU=["Smith, John"],
        PY=2020,
    )

    with caplog.at_level(logging.DEBUG, logger="maiba.scoring"):
        resolver.resolve(item)

    top_lines = [
        r.getMessage()
        for r in caplog.records
        if r.name == "maiba.scoring" and r.getMessage().lstrip().startswith("top")
    ]
    starred = [m for m in top_lines if " * " in m]
    assert len(starred) == 1, (
        f"expected exactly one starred top line; got {len(starred)} in {top_lines}"
    )
