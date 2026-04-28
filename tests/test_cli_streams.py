"""Tests for the Unix-pipeable CLI (ticket 0010).

All tests use subprocess so they exercise the real CLI entry point.
The fixture `tests/fixtures/good.ris` has no gaps (TI, AU, PY all present,
no forbidden authors), so no network calls are made during these tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
GOOD = ROOT / "tests" / "fixtures" / "good.ris"


def _run(args: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "maiba", *args],
        input=stdin,
        capture_output=True,
        cwd=ROOT,
    )


def test_no_args_prints_help_exit_zero():
    r = _run([])
    assert r.returncode == 0
    assert b"usage: maiba" in r.stdout
    assert b"scan" in r.stdout  # primary verb
    assert b"clear-cache" in r.stdout  # cache verb (proves real help, not stub)


def test_scan_file_to_stdout(tmp_path):
    r = _run(["scan", "-i", str(GOOD)])
    assert r.returncode == 0
    assert b"TY  - JOUR" in r.stdout
    # No file written
    assert not list(tmp_path.iterdir())


def test_scan_stdin_to_stdout():
    data = GOOD.read_bytes()
    r = _run(["scan"], stdin=data)
    assert r.returncode == 0
    assert b"TY  - JOUR" in r.stdout


def test_scan_file_to_file(tmp_path):
    out = tmp_path / "out.ris"
    r = _run(["scan", "-i", str(GOOD), "-o", str(out)])
    assert r.returncode == 0
    assert out.exists()
    assert "TY  - JOUR" in out.read_text(encoding="utf-8")


def test_positional_input_is_rejected(tmp_path):
    """Old positional form must error — no backward-compat shim."""
    out = tmp_path / "out.ris"
    r = _run(["scan", str(GOOD), "-o", str(out)])
    assert r.returncode != 0
    assert not out.exists()


def test_scan_stdin_to_stdout_keeps_summary_off_stdout():
    """Summary must go to stderr, not stdout, when streaming RIS to stdout."""
    data = GOOD.read_bytes()
    r = _run(["scan"], stdin=data)
    assert r.returncode == 0
    assert b"TY  - " in r.stdout
    assert b"Scanned:" not in r.stdout  # summary must NOT pollute stream
    assert b"Scanned:" in r.stderr  # but it must still appear somewhere
