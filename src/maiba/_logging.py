"""Logging configuration helper.

Verbosity 0 (default) → WARNING; 1 → INFO; 2+ → DEBUG. Logs go to
stderr so they interleave naturally with progress glyphs and don't
pollute stdout (which carries the corrected RIS in stream mode).
"""

from __future__ import annotations

import logging
import sys

_LEVEL_FROM_VERBOSITY = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}

_NOISY_LIBRARIES = ("httpx", "httpcore", "urllib3")


def configure(verbosity: int) -> None:
    """Set up the root logger.

    Stream is stderr. Format is short and human-readable (timestamp,
    level, logger name, message). Forces reconfiguration so multiple
    calls in tests are idempotent.

    Third-party libraries (httpx, httpcore, urllib3) are pinned to
    WARNING unless verbosity >= 2 — otherwise INFO floods the output.
    """
    level = _LEVEL_FROM_VERBOSITY.get(verbosity, logging.DEBUG)
    logging.basicConfig(
        level=level,
        # Leading \n so log lines don't run into the inline glyph stream
        # printed by pipeline.py during -v scans.
        format="\n%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
    # The root level above is correct, but setting `maiba` explicitly
    # makes the contract obvious to callers querying getEffectiveLevel().
    logging.getLogger("maiba").setLevel(level)
    if verbosity < 2:
        for noisy in _NOISY_LIBRARIES:
            logging.getLogger(noisy).setLevel(logging.WARNING)
    else:
        # At -vv, let third-party libraries inherit the root DEBUG level
        # so users can see HTTP traffic. NOTSET clears any prior pinning.
        for noisy in _NOISY_LIBRARIES:
            logging.getLogger(noisy).setLevel(logging.NOTSET)
