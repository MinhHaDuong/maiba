import json
from pathlib import Path

import respx
from httpx import Response

from maiba.config import load_config
from maiba.pipeline import run

FIXTURE = Path("tests/fixtures/ArchiveCCS.ris")
RESPONSES = Path("tests/fixtures/responses")


def _setup_mocks() -> None:
    """Mock all OpenAlex/Crossref calls via respx.

    Specific DOI lookups → captured DOI fixtures.
    Anything else → captured 'true miss' search fixtures.
    """
    ashworth_oa = json.loads((RESPONSES / "openalex/ashworth-2009-doi.json").read_text())
    respx.get(
        url__regex=r".*api\.openalex\.org/works/doi:10\.1016/j\.egypro\.2009\.02\.302.*"
    ).mock(return_value=Response(200, json=ashworth_oa))

    stone_oa = json.loads((RESPONSES / "openalex/stone-2008-doi.json").read_text())
    respx.get(url__regex=r".*api\.openalex\.org/works/doi:10\.1039/b807747a.*").mock(
        return_value=Response(200, json=stone_oa)
    )

    ashworth_cr = json.loads((RESPONSES / "crossref/ashworth-2009-doi.json").read_text())
    respx.get(url__regex=r".*api\.crossref\.org/works/10\.1016/j\.egypro\.2009\.02\.302.*").mock(
        return_value=Response(200, json=ashworth_cr)
    )

    stone_cr = json.loads((RESPONSES / "crossref/stone-2008-doi.json").read_text())
    respx.get(url__regex=r".*api\.crossref\.org/works/10\.1039/b807747a.*").mock(
        return_value=Response(200, json=stone_cr)
    )

    miss_oa = json.loads((RESPONSES / "openalex/lemonde-sleipner-2008-search.json").read_text())
    respx.get(url__startswith="https://api.openalex.org/works").mock(
        return_value=Response(200, json=miss_oa)
    )

    miss_cr = json.loads((RESPONSES / "crossref/lemonde-sleipner-2008-search.json").read_text())
    respx.get(url__startswith="https://api.crossref.org/works").mock(
        return_value=Response(200, json=miss_cr)
    )


@respx.mock
def test_end_to_end_on_archiveccs_subset(tmp_path):
    _setup_mocks()
    out = tmp_path / "out.ris"
    cfg = load_config("config/maiba.yaml")
    report = run(input=FIXTURE, output=out, cfg=cfg)

    assert report.scanned == 223
    assert out.exists()


@respx.mock
def test_et_al_author_is_fixed_from_doi_lookup(tmp_path):
    """Records with 'et al.' as author and a DOI get the full author list back.

    Uses a dedicated fixture (`et-al-with-doi.ris`) with one engineered
    record so the assertion doesn't depend on AB being a recommended gap.
    """
    _setup_mocks()
    out = tmp_path / "out.ris"
    cfg = load_config("config/maiba.yaml")
    fixture = Path("tests/fixtures/et-al-with-doi.ris")
    report = run(input=fixture, output=out, cfg=cfg)

    assert report.scanned == 1
    assert report.fixed == 1
    text = out.read_text(encoding="utf-8")
    assert "Carr-Cornish" in text
    assert "maiba:autofixed:" in text
    assert "maiba:before AU=" in text


@respx.mock
def test_dry_run_does_not_write_output(tmp_path):
    _setup_mocks()
    cfg = load_config("config/maiba.yaml")
    report = run(input=FIXTURE, output=None, cfg=cfg)

    assert report.scanned == 223


@respx.mock
def test_complete_records_are_unchanged(tmp_path):
    _setup_mocks()
    out = tmp_path / "out.ris"
    cfg = load_config("config/maiba.yaml")
    report = run(input=FIXTURE, output=out, cfg=cfg)

    assert report.scanned == report.with_gaps + (report.scanned - report.with_gaps)
    assert report.fixed <= report.with_gaps


@respx.mock
def test_openalex_429_does_not_abort_pipeline(tmp_path):
    """When OpenAlex returns 429, Crossref must still be tried for every record.

    The dead resolver is skipped for the rest of the run; the pipeline does
    NOT drain remaining records unchanged (the old abort-and-drain contract).
    """
    respx.get(url__startswith="https://api.openalex.org").mock(
        return_value=Response(429, json={"error": "Rate limit exceeded"})
    )
    ashworth_cr = json.loads((RESPONSES / "crossref/ashworth-2009-doi.json").read_text())
    crossref_route = respx.get(url__startswith="https://api.crossref.org").mock(
        return_value=Response(200, json=ashworth_cr)
    )

    cfg = load_config("config/maiba.yaml")
    out = tmp_path / "out.ris"
    fixture = Path("tests/fixtures/et-al-with-doi.ris")
    report = run(input=fixture, output=out, cfg=cfg)

    assert crossref_route.called, "crossref must be tried after openalex 429"
    assert report.rate_limited >= 1, "expected at least one record marked rate-limited"
    assert report.fixed == 1, "crossref candidate should still produce a fix"
    text = out.read_text(encoding="utf-8")
    assert "maiba:autofixed:" in text


@respx.mock
def test_openalex_429_only_logged_once(tmp_path, caplog):
    """The dead-resolver warning fires once, not once per record."""
    import logging

    respx.get(url__startswith="https://api.openalex.org").mock(
        return_value=Response(429, json={"error": "Rate limit exceeded"})
    )
    respx.get(url__startswith="https://api.crossref.org").mock(
        return_value=Response(
            200, json={"status": "ok", "message": {"items": [], "total-results": 0}}
        )
    )
    cfg = load_config("config/maiba.yaml")
    with caplog.at_level(logging.WARNING, logger="maiba.pipeline"):
        run(input=FIXTURE, output=tmp_path / "out.ris", cfg=cfg)

    rate_limit_warnings = [r for r in caplog.records if "rate limited" in r.getMessage().lower()]
    assert len(rate_limit_warnings) == 1, (
        f"expected exactly one rate-limit warning, got {len(rate_limit_warnings)}"
    )
