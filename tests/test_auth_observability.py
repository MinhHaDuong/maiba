"""Adherence: .env propagates to OpenAlex resolver headers.

If `.env` contains OPENALEX_API_KEY, by the time the resolver runs
its httpx client must carry `Authorization: Bearer <key>`. Locks the
load-order contract from ticket 0017 against future regressions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

CONFIG = Path(__file__).resolve().parent.parent / "config" / "maiba.yaml"


def test_dotenv_propagates_to_openalex_authorization_header(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling main() with .env in cwd makes the resolver carry Bearer auth."""
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENALEX_API_KEY=test-sentinel-xxx\n")

    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))

    from maiba.config import load_config
    from maiba.resolvers.openalex import OpenAlexResolver

    cfg = load_config(CONFIG)
    resolver = OpenAlexResolver(cfg)
    headers = resolver._client.headers
    assert headers.get("Authorization") == "Bearer test-sentinel-xxx"


def test_auth_status_warning_logged_when_key_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Default-verbosity users see a WARNING when OPENALEX_API_KEY is not set.

    `cli.configure_logging(force=True)` wipes pytest's caplog handler, so we
    capture stderr directly rather than via `caplog`.
    """
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    from maiba.cli import main

    fixture = tmp_path / "in.ris"
    fixture.write_text("TY  - JOUR\nTI  - x\nER  - \n")

    main(["scan", "-i", str(fixture), "-o", str(tmp_path / "out.ris"), "--config", str(CONFIG)])

    err = capsys.readouterr().err
    assert "OPENALEX_API_KEY not set" in err, (
        f"expected WARNING about missing OPENALEX_API_KEY in stderr; got: {err!r}"
    )


def test_auth_status_info_logged_when_key_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verbose users see an INFO line confirming the key was detected."""
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key-12345")
    monkeypatch.chdir(tmp_path)

    from maiba.cli import main

    fixture = tmp_path / "in.ris"
    fixture.write_text("TY  - JOUR\nTI  - x\nER  - \n")

    main(
        [
            "scan",
            "-v",
            "-i",
            str(fixture),
            "-o",
            str(tmp_path / "out.ris"),
            "--config",
            str(CONFIG),
        ]
    )

    err = capsys.readouterr().err
    assert "OpenAlex auth: detected" in err
    assert "test-key-12345" not in err, "key value must never appear in logs"
