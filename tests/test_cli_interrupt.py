"""Ctrl+C handling: short message, exit 130, no traceback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from maiba.cli import main


def test_keyboard_interrupt_returns_130_with_clean_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ctrl+C during scan exits 130 with a short message and no traceback."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("")
    fixture = tmp_path / "in.ris"
    fixture.write_text("TY  - JOUR\nTI  - x\nER  - \n")

    config_path = Path(__file__).resolve().parent.parent / "config" / "maiba.yaml"
    with patch("maiba.cli.run", side_effect=KeyboardInterrupt):
        rc = main(
            [
                "scan",
                "-i",
                str(fixture),
                "-o",
                str(tmp_path / "out.ris"),
                "--config",
                str(config_path),
            ]
        )

    assert rc == 130
    captured = capsys.readouterr()
    assert "aborted by user" in captured.err.lower()
    assert "traceback" not in captured.err.lower()
