"""MAIBA CLI entry point."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from maiba._logging import configure as configure_logging
from maiba.config import load_config
from maiba.pipeline import run


def _build_parser() -> argparse.ArgumentParser:
    # `-v` lives on each subparser (post-verb position, like git commit -v).
    # Defining it on each via a shared parent avoids the argparse footgun
    # where parents= on both top-level and subparsers makes the subparser's
    # default clobber the top-level value.
    verbose_parent = argparse.ArgumentParser(add_help=False)
    verbose_parent.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v INFO, -vv DEBUG; default WARNING)",
    )

    parser = argparse.ArgumentParser(prog="maiba", description="MAIBA — bibliography janitor")
    sub = parser.add_subparsers(dest="cmd", required=False)

    scan = sub.add_parser(
        "scan",
        parents=[verbose_parent],
        help="Scan an RIS file and optionally fix gaps",
    )
    scan.add_argument(
        "-i",
        "--input",
        type=Path,
        default=None,
        help="Input .ris file (default: read from stdin)",
    )
    scan.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .ris file (default: write corrected RIS to stdout)",
    )
    scan.add_argument(
        "--config", type=Path, default=Path("config/maiba.yaml"), help="Path to maiba.yaml"
    )
    scan.add_argument(
        "--llm-fallback", action="store_true", help="Enable LLM fallback (not implemented in MVP)"
    )
    scan.add_argument("--report", type=Path, default=None, help="Write a markdown report")
    scan.add_argument("--quiet", action="store_true", help="Suppress per-record progress glyphs")
    scan.add_argument(
        "--cache",
        action="store_true",
        help=(
            "Cache OpenAlex/Crossref responses on disk (default: off). "
            "Cache lives at config http.cache_dir (default ~/.cache/maiba/http/); "
            "delete the directory or run 'maiba clear-cache' to wipe."
        ),
    )

    cc = sub.add_parser(
        "clear-cache",
        parents=[verbose_parent],
        help="Remove the HTTP response cache directory (only relevant if --cache was used)",
    )
    cc.add_argument(
        "--config", type=Path, default=Path("config/maiba.yaml"), help="Path to maiba.yaml"
    )

    return parser


def _resolve_input(args: argparse.Namespace) -> tuple[Path, Path | None]:
    """Return (input_path, input_tmp_to_delete).

    Buffers stdin to a tempfile when no --input flag is given and stdin is piped.
    The caller must unlink `input_tmp_to_delete` after the pipeline finishes.
    Exits with code 2 if neither a file nor a piped stdin is available.
    """
    if args.input is not None:
        return args.input, None
    if not sys.stdin.isatty():
        with tempfile.NamedTemporaryFile(suffix=".ris", delete=False) as tmp:
            shutil.copyfileobj(sys.stdin.buffer, tmp)
            tmp_path = Path(tmp.name)
        return tmp_path, tmp_path
    sys.stderr.write(
        "error: no input file given and stdin is a TTY.\n"
        "Usage: maiba scan -i FILE.ris  OR  cat FILE.ris | maiba scan\n"
    )
    raise SystemExit(2)


def _cmd_scan(args: argparse.Namespace) -> int:
    """Execute the `scan` subcommand."""
    cfg = load_config(args.config)
    input_path, input_tmp = _resolve_input(args)

    # When no --output given, use a tempfile as the pipeline output, then
    # stream its contents to stdout after the run.
    output_tmp: Path | None = None
    output: Path | None = args.output
    stream_to_stdout = output is None
    if stream_to_stdout:
        with tempfile.NamedTemporaryFile(suffix=".ris", delete=False) as tmp:
            output_tmp = Path(tmp.name)
        output = output_tmp

    report = run(
        input=input_path,
        output=output,
        cfg=cfg,
        quiet=args.quiet,
        use_cache=args.cache,
    )

    if input_tmp is not None:
        _try_unlink(input_tmp)

    if stream_to_stdout and output_tmp is not None:
        # Copy corrected RIS to stdout; summary goes to stderr to avoid
        # corrupting the piped data stream.
        sys.stdout.buffer.write(output_tmp.read_bytes())
        sys.stdout.flush()
        _try_unlink(output_tmp)
        _print_summary(report, output=None, file=sys.stderr)
    else:
        _print_summary(report, output=args.output, file=sys.stdout)

    if args.report is not None:
        _write_report(args.report, report)

    return 0


def _try_unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    # Auto-load .env starting from cwd (not from this file's location)
    # before any os.environ reads. Existing shell exports take precedence.
    load_dotenv(find_dotenv(usecwd=True))
    parser = _build_parser()
    args = parser.parse_args(argv)
    # verbose only exists on subcommands; safe default for the no-args path.
    configure_logging(getattr(args, "verbose", 0))

    if args.cmd is None:
        parser.print_help()
        return 0

    if args.cmd == "clear-cache":
        return _clear_cache(args)

    if args.llm_fallback:
        parser.error("--llm-fallback is not implemented in MVP")

    try:
        return _cmd_scan(args)
    except KeyboardInterrupt:
        print("\naborted by user (Ctrl+C)", file=sys.stderr, flush=True)
        return 130


def _clear_cache(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    cache_dir = Path(cfg.http.cache_dir).expanduser()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"Removed cache directory: {cache_dir}")
    else:
        print(f"Cache directory does not exist: {cache_dir}")
    return 0


def _print_summary(report, output: Path | None, file=None) -> None:  # noqa: ANN001
    if file is None:
        file = sys.stdout
    print(f"Scanned: {report.scanned}", file=file)
    print(f"With gaps: {report.with_gaps}", file=file)
    print(f"Fixed: {report.fixed}", file=file)
    print(f"Skipped (below threshold): {report.skipped_below_threshold}", file=file)
    if output is not None:
        print(f"Output: {output}", file=file)


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
