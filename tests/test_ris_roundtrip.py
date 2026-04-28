from pathlib import Path

import pytest

from maiba.ris import RisParseError, read_ris, write_ris

F = Path("tests/fixtures")


def test_good_parses_three_records():
    items = list(read_ris(F / "good.ris"))
    assert len(items) == 3
    assert {it.TY for it in items} == {"JOUR", "RPRT", "NEWS"}


def test_good_roundtrip_is_stable(tmp_path):
    items = list(read_ris(F / "good.ris"))
    out = tmp_path / "out.ris"
    write_ris(items, out)
    assert list(read_ris(out)) == items


def test_archiveccs_parses_to_223_items():
    items = list(read_ris(F / "ArchiveCCS.ris"))
    assert len(items) == 223


def test_archiveccs_roundtrip_is_stable(tmp_path):
    items = list(read_ris(F / "ArchiveCCS.ris"))
    out = tmp_path / "out.ris"
    write_ris(items, out)
    assert list(read_ris(out)) == items


def test_archiveccs_known_doi_record_has_expected_fields():
    ash = next(
        it for it in read_ris(F / "ArchiveCCS.ris") if it.DO == "10.1016/j.egypro.2009.02.302"
    )
    assert ash.TY == "JOUR"
    assert ash.JO == "Energy Procedia"
    assert "Ashworth" in " ".join(ash.AU)
    assert ash.id.startswith("Ashworth.ea-2009-EngagingThePublic")


def test_empty_returns_no_items():
    assert list(read_ris(F / "empty.ris")) == []


@pytest.mark.parametrize(
    "name",
    [
        "bad-notaris.ris",
        "bad-no-er.ris",
        "bad-no-ty.ris",
        "bad-malformed-tag.ris",
        "bad-truncated-mid-record.ris",
        "bad-binaryfile.ris",
    ],
)
def test_bad_inputs_raise(name):
    with pytest.raises(RisParseError):
        list(read_ris(F / name))
