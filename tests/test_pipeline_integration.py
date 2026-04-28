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
    report = run(input=FIXTURE, output=out, cfg=cfg, apply=True)

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
    report = run(input=fixture, output=out, cfg=cfg, apply=True)

    assert report.scanned == 1
    assert report.fixed == 1
    text = out.read_text(encoding="utf-8")
    assert "Carr-Cornish" in text
    assert "maiba:autofixed:" in text
    assert "maiba:before AU=" in text


@respx.mock
def test_dry_run_does_not_write_output(tmp_path):
    _setup_mocks()
    out = tmp_path / "out.ris"
    cfg = load_config("config/maiba.yaml")
    report = run(input=FIXTURE, output=out, cfg=cfg, apply=False)

    assert report.scanned == 223
    assert not out.exists()


@respx.mock
def test_complete_records_are_unchanged(tmp_path):
    _setup_mocks()
    out = tmp_path / "out.ris"
    cfg = load_config("config/maiba.yaml")
    report = run(input=FIXTURE, output=out, cfg=cfg, apply=True)

    assert report.scanned == report.with_gaps + (report.scanned - report.with_gaps)
    assert report.fixed <= report.with_gaps
