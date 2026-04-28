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
