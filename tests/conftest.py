"""Test fixtures shared by every test in the suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_openalex_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip OPENALEX_API_KEY from the test environment.

    Tests that need the key set use ``monkeypatch.setenv`` themselves.
    Without this autouse fixture, a developer's shell environment would
    silently leak into the resolver-construction tests.
    """
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
