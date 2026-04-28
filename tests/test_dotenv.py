"""Tests for the .env auto-load behavior at CLI startup."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from maiba.cli import main


def test_dotenv_is_loaded_from_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A .env file in cwd populates os.environ at CLI startup."""
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENALEX_API_KEY=from-dotenv\n")

    main([])  # no-args → prints help + exits 0

    assert os.environ.get("OPENALEX_API_KEY") == "from-dotenv"


def test_explicit_env_wins_over_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Shell-exported env vars take precedence over .env values."""
    monkeypatch.setenv("OPENALEX_API_KEY", "from-shell")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENALEX_API_KEY=from-dotenv\n")

    main([])

    assert os.environ.get("OPENALEX_API_KEY") == "from-shell"
