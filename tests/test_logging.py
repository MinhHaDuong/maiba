"""Tests for the verbosity-aware logging helper."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import respx
from httpx import Response

from maiba._logging import configure
from maiba.config import load_config
from maiba.pipeline import run


def test_configure_default_is_warning() -> None:
    configure(0)
    assert logging.getLogger("maiba").getEffectiveLevel() == logging.WARNING


def test_configure_verbose_is_info() -> None:
    configure(1)
    assert logging.getLogger("maiba").getEffectiveLevel() == logging.INFO


def test_configure_double_verbose_is_debug() -> None:
    configure(2)
    assert logging.getLogger("maiba").getEffectiveLevel() == logging.DEBUG


def test_third_party_libraries_pinned_to_warning_at_default() -> None:
    configure(0)
    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


def test_third_party_libraries_unpinned_at_double_verbose() -> None:
    configure(2)
    # At -vv, third-party libraries inherit the root DEBUG level
    # rather than being explicitly pinned to WARNING.
    assert logging.getLogger("httpx").getEffectiveLevel() == logging.DEBUG


@respx.mock
def test_pipeline_logs_per_record_at_info(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """The pipeline emits at least one INFO record about the scan."""
    respx.get(url__startswith="https://api.openalex.org").mock(
        return_value=Response(200, json={"meta": {"count": 0}, "results": []})
    )
    respx.get(url__startswith="https://api.crossref.org").mock(
        return_value=Response(
            200,
            json={"status": "ok", "message": {"items": [], "total-results": 0}},
        )
    )
    cfg = load_config(Path("config/maiba.yaml"))
    with caplog.at_level(logging.INFO, logger="maiba.pipeline"):
        run(
            input=Path("tests/fixtures/good.ris"),
            output=tmp_path / "out.ris",
            cfg=cfg,
        )
    pipeline_records = [r for r in caplog.records if r.name == "maiba.pipeline"]
    assert pipeline_records, "expected at least one INFO log from maiba.pipeline"
