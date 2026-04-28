import sys
from pathlib import Path

import pytest
import respx
from httpx import Response

from maiba.config import load_config
from maiba.pipeline import _classify, run


@respx.mock
def test_progress_glyph_per_record_on_tty(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    # Default-deny network: no resolver hits; every gapped record gets `0`.
    respx.get(url__startswith="https://api.openalex.org").mock(
        return_value=Response(200, json={"meta": {"count": 0}, "results": []})
    )
    respx.get(url__startswith="https://api.crossref.org").mock(
        return_value=Response(
            200,
            json={"status": "ok", "message": {"items": [], "total-results": 0}},
        )
    )
    cfg = load_config("config/maiba.yaml")
    run(
        input=Path("tests/fixtures/good.ris"),
        output=tmp_path / "out.ris",
        cfg=cfg,
        apply=False,
    )
    err = capsys.readouterr().err
    # Output is: announce line + glyphs + trailing newline.
    assert err.startswith("Scanning 3 records")
    glyphs = err.splitlines()[-1]
    assert len(glyphs) == 3
    assert all(c in ".0*+" for c in glyphs)
    assert err.endswith("\n")


def test_progress_suppressed_when_stderr_not_tty(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    cfg = load_config("config/maiba.yaml")
    # Empty fixture → loop doesn't fire either way; verifies no crash on non-tty.
    run(
        input=Path("tests/fixtures/empty.ris"),
        output=tmp_path / "out.ris",
        cfg=cfg,
        apply=False,
    )
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    ("gaps", "changed", "expected"),
    [
        (0, 0, "."),
        (3, 0, "0"),
        (2, 2, "*"),
        (3, 5, "*"),
        (3, 1, "+"),
    ],
)
def test_classify_helper(gaps, changed, expected):
    assert _classify(gaps, changed) == expected
