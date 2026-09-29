from zipfile import ZipFile

import pytest

from backend.app.services.rag.chunker import chunk_case, chunk_text


@pytest.fixture
def ingestion_api():
    loaders = pytest.importorskip("backend.app.services.ingestion.loaders")
    parser = pytest.importorskip("backend.app.services.ingestion.parser")

    load_document = getattr(loaders, "load_document", None)
    parse_document = getattr(parser, "parse_document", None)
    if not callable(load_document) or not callable(parse_document):
        pytest.skip("Person 3 ingestion interface is not merged yet")
    return load_document, parse_document


def _write_docx(path, text):
    document_xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>"""
    with ZipFile(path, "w") as document:
        document.writestr("[Content_Types].xml", """<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>""")
        document.writestr("word/document.xml", document_xml)


def _write_pdf(path, text):
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(pdf)


@pytest.mark.parametrize("extension", ["txt", "docx", "pdf"])
def test_load_and_parse_supported_documents(tmp_path, ingestion_api, extension):
    load_document, parse_document = ingestion_api
    path = tmp_path / f"sample.{extension}"
    expected = "A small legal document."

    if extension == "txt":
        path.write_text(expected, encoding="utf-8")
    elif extension == "docx":
        _write_docx(path, expected)
    else:
        _write_pdf(path, expected)

    loaded = load_document(path)
    parsed = parse_document(loaded)

    assert expected in parsed


def test_empty_file_returns_no_text(tmp_path, ingestion_api):
    load_document, parse_document = ingestion_api
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    assert parse_document(load_document(path)) == ""


def test_unsupported_extension_is_rejected(tmp_path, ingestion_api):
    load_document, _ = ingestion_api
    path = tmp_path / "sample.csv"
    path.write_text("not supported", encoding="utf-8")

    with pytest.raises((ValueError, TypeError)):
        load_document(path)


def test_corrupt_document_is_rejected(tmp_path, ingestion_api):
    load_document, _ = ingestion_api
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"not a valid PDF")

    with pytest.raises((ValueError, TypeError, OSError)):
        load_document(path)


def test_empty_text_produces_no_chunks():
    assert chunk_text("   ") == []


def test_chunk_text_overlaps_and_preserves_content():
    text = "alpha " * 120
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(piece for piece, _, _ in chunks)
    assert chunks[0][1] == 0
    assert chunks[-1][2] == len(text.strip())
    assert any(first[2] > second[1] for first, second in zip(chunks, chunks[1:]))


def test_invalid_overlap_is_rejected():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("some text", chunk_size=10, overlap=10)


def test_chunk_case_carries_metadata_and_positions():
    case = {
        "case_number": "80343",
        "case_index": 2,
        "volume": 15,
        "legal_category": "contract",
        "page_range": "1-2",
        "context": "A legal decision with enough text for one chunk.",
    }
    chunks = chunk_case(case, chunk_size=800, overlap=100)
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "80343_0"
    assert chunks[0]["legal_category"] == "contract"
    assert chunks[0]["char_start"] == 0
