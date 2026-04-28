"""Mechanical hygiene ratchets for src/maiba/ and config/maiba.yaml.

These tests catch project-specific invariants that ruff cannot express:
- print() must be explicit about its target stream (or live in cli.py)
- API endpoints and contact details live in config, not in code
- The shipped config and the Config pydantic model agree on field set
- The CLI uses stdlib argparse, not click/typer

Use a trailing `# noqa: hygiene` comment to declare a one-off exception
when justified (e.g. stripping a known URL prefix from a string).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.adherence

SRC = Path("src/maiba")
CONFIG = Path("config/maiba.yaml")
HTTP_URL_RE = re.compile(r"https?://[a-zA-Z0-9.-]+")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
NOQA = "# noqa: hygiene"


def _src_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_print_outside_cli_must_target_explicit_stream():
    """print() in non-cli.py modules must use file=... explicitly.

    cli.py is exempt: its job is to write a human-readable summary to
    stdout. Everything else (e.g. progress glyphs in pipeline.py) must
    say where the bytes go — typically file=sys.stderr.
    """
    offenders: list[str] = []
    for path in _src_files():
        if path.name == "cli.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
                and not any(kw.arg == "file" for kw in node.keywords)
            ):
                offenders.append(f"{path}:{node.lineno}")
    assert not offenders, "print() without explicit file=: " + ", ".join(offenders)


def test_no_hardcoded_http_urls_in_src():
    """API endpoints live in config/maiba.yaml, not in code."""
    offenders: list[str] = []
    for path in _src_files():
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if HTTP_URL_RE.search(line) and NOQA not in line:
                offenders.append(f"{path}:{i}: {line.strip()}")
    assert not offenders, "Hardcoded URL — move to config: " + "; ".join(offenders)


def test_no_hardcoded_email_in_src():
    """mailto / contact lives in config/maiba.yaml under contact.mailto."""
    offenders: list[str] = []
    for path in _src_files():
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if EMAIL_RE.search(line) and NOQA not in line:
                offenders.append(f"{path}:{i}: {line.strip()}")
    assert not offenders, "Hardcoded email — move to config: " + "; ".join(offenders)


def test_config_yaml_roundtrips_through_pydantic_model():
    """config/maiba.yaml must load cleanly into Config and round-trip
    via model_dump → yaml → load_config back to an equal model.

    This catches drift between the shipped YAML and the model schema.
    """
    from maiba.config import Config, load_config

    cfg = load_config(CONFIG)
    redumped = yaml.safe_load(yaml.safe_dump(cfg.model_dump(mode="json")))
    cfg_back = Config.model_validate(redumped)
    assert cfg == cfg_back


def test_cli_uses_stdlib_argparse():
    """KISS — no click, no typer."""
    cli = SRC / "cli.py"
    text = cli.read_text(encoding="utf-8")
    assert "import argparse" in text or "from argparse" in text, (
        "src/maiba/cli.py must use stdlib argparse"
    )
    assert "import click" not in text and "from click" not in text, (
        "click is not used in this project"
    )
    assert "import typer" not in text and "from typer" not in text, (
        "typer is not used in this project"
    )


def test_resolvers_use_shared_scoring():
    """Both resolvers must delegate to the shared scorer, not inline the math.

    Ticket 0013 fix: the inline `title_sim * 0.7 + overlap * 0.3` formula
    rejected items with missing AU even when the title was a perfect
    match. Ratcheted here so a regression to inline math fails CI. The
    shared entry point is `select_best_candidate` (ticket 0025); a
    direct `score_candidate` call also satisfies the contract.
    """
    for name in ("openalex.py", "crossref.py"):
        path = SRC / "resolvers" / name
        src = path.read_text(encoding="utf-8")
        assert "title_sim * 0.7" not in src, f"{path}: inline scoring formula"
        assert "select_best_candidate(" in src or "score_candidate(" in src, (
            f"{path}: must call shared scorer"
        )
