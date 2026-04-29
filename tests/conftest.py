"""Test fixtures shared by every test in the suite."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from pypdf import PdfWriter

_XMP_XML = (
    '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
    '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
    "<dc:title><rdf:Alt>"
    '<rdf:li xml:lang="x-default">MAIBA XMP Test Title</rdf:li>'
    "</rdf:Alt></dc:title>\n"
    "<dc:creator><rdf:Seq>"
    "<rdf:li>xmp-test-author</rdf:li>"
    "</rdf:Seq></dc:creator>\n"
    "</rdf:Description>\n"
    "</rdf:RDF>\n"
    "</x:xmpmeta>\n"
    '<?xpacket end="r"?>'
)


def _build_pdf_with_xmp(xmp_xml: str) -> bytes:
    """Build minimal 1-page PDF bytes with an embedded XMP metadata stream."""
    xmp_bytes = xmp_xml.encode("utf-8")
    objs: list[bytes] = []
    offsets: list[int] = []
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

    def emit(b: bytes) -> None:
        offsets.append(sum(len(o) for o in objs))
        objs.append(b)

    emit(b"1 0 obj\n<</Type /Catalog /Pages 2 0 R /Metadata 4 0 R>>\nendobj\n")
    emit(b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n")
    emit(b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 100 100]>>\nendobj\n")
    emit(
        f"4 0 obj\n<</Type /Metadata /Subtype /XML /Length {len(xmp_bytes)}>>\nstream\n".encode()
        + xmp_bytes
        + b"\nendstream\nendobj\n"
    )
    body = b"".join(objs)
    base = len(header)
    xref_pos = base + len(body)
    xref_lines = ["xref\n", "0 5\n", "0000000000 65535 f \n"]
    xref_lines += [f"{base + o:010d} 00000 n \n" for o in offsets]
    trailer = f"trailer\n<</Size 5 /Root 1 0 R>>\nstartxref\n{xref_pos}\n%%EOF\n"
    return header + body + "".join(xref_lines).encode() + trailer.encode()


@pytest.fixture(scope="session")
def pdf_info_dict_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Minimal PDF with /Title and /Author in the info dict."""
    p = tmp_path_factory.mktemp("pdfs") / "info-dict.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata(
        {"/Title": "MAIBA Info-Dict Test Title", "/Author": "MAIBA Info-Dict Author"}
    )
    buf = io.BytesIO()
    writer.write(buf)
    p.write_bytes(buf.getvalue())
    return p


@pytest.fixture(scope="session")
def pdf_xmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Minimal PDF with dc:title and dc:creator in XMP metadata."""
    p = tmp_path_factory.mktemp("pdfs") / "xmp-meta.pdf"
    p.write_bytes(_build_pdf_with_xmp(_XMP_XML))
    return p


@pytest.fixture(scope="session")
def pdf_bad_xmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """PDF whose XMP stream contains malformed XML (real-world occurrence)."""
    p = tmp_path_factory.mktemp("pdfs") / "bad-xmp.pdf"
    p.write_bytes(_build_pdf_with_xmp("<not-valid-xml"))
    return p


@pytest.fixture(autouse=True)
def _no_openalex_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip OPENALEX_API_KEY from the test environment.

    Tests that need the key set use ``monkeypatch.setenv`` themselves.
    Without this autouse fixture, a developer's shell environment would
    silently leak into the resolver-construction tests.
    """
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
