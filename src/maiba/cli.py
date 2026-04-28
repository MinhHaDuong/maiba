"""MAIBA CLI entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from maiba.config import load_config
from maiba.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="maiba", description="MAIBA — bibliography janitor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="Scan an RIS file and optionally fix gaps")
    scan.add_argument("input", type=Path, help="Input .ris file")
    scan.add_argument("-o", "--output", type=Path, default=None, help="Output .ris file")
    scan.add_argument(
        "--config", type=Path, default=Path("config/maiba.yaml"), help="Path to maiba.yaml"
    )
    scan.add_argument("--apply", action="store_true", help="Write corrected RIS to output")
    scan.add_argument(
        "--llm-fallback", action="store_true", help="Enable LLM fallback (not implemented in MVP)"
    )
    scan.add_argument("--report", type=Path, default=None, help="Write a markdown report")
    scan.add_argument("--quiet", action="store_true", help="Suppress per-record progress glyphs")

    args = parser.parse_args(argv)

    if args.llm_fallback:
        parser.error("--llm-fallback is not implemented in MVP")

    cfg = load_config(args.config)

    output: Path | None = args.output
    if args.apply and output is None:
        output = args.input.with_suffix(".fixed.ris")

    report = run(input=args.input, output=output, cfg=cfg, apply=args.apply, quiet=args.quiet)

    print(f"Scanned: {report.scanned}")
    print(f"With gaps: {report.with_gaps}")
    print(f"Fixed: {report.fixed}")
    print(f"Skipped (below threshold): {report.skipped_below_threshold}")
    if args.apply and output is not None:
        print(f"Output: {output}")

    if args.report is not None:
        _write_report(args.report, report)

    return 0


def _write_report(path: Path, report) -> None:  # noqa: ANN001
    lines = [
        "# MAIBA scan report",
        "",
        f"- Scanned: {report.scanned}",
        f"- With gaps: {report.with_gaps}",
        f"- Fixed: {report.fixed}",
        f"- Skipped (below threshold): {report.skipped_below_threshold}",
        "",
        "## Fixes",
        "",
    ]
    for fix in report.fixes:
        lines.append(
            f"- `{fix.item_id}` ({fix.source}, conf={fix.confidence:.2f}): "
            f"{', '.join(fix.fields_changed.keys())}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
