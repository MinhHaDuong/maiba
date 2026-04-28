"""Ratchet: no half-finished work in committed code.

Stubs (`NotImplementedError`), skip-marked tests (`pytest.skip`,
`@pytest.mark.skip`), and TODO comments are signals of deferred work
that someone "will come back to." In autonomous-TDD codebases, nobody
does. Use a follow-up ticket instead.

Escape hatch: `# noqa: hygiene` on the line if the marker is genuinely
load-bearing (rare).
"""

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "maiba"

PATTERNS = [
    (r"\bNotImplementedError\b", "NotImplementedError"),
    (r"@pytest\.mark\.skip\b|pytest\.skip\(", "pytest.skip"),
    (r"#\s*TODO\b", "TODO"),
]


@pytest.mark.parametrize("pattern,name", PATTERNS, ids=[n for _, n in PATTERNS])
def test_no_stubs_or_skips_or_todos_in_src(pattern, name):
    rx = re.compile(pattern)
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if rx.search(line) and "noqa: hygiene" not in line:
                offenders.append(f"{path.relative_to(SRC.parent.parent)}:{i}: {line.strip()}")
    assert not offenders, f"{name} found:\n  " + "\n  ".join(offenders)
