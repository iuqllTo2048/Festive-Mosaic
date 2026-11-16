import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.config import Settings
from app.main import create_app


def make_pdf(page_texts: list[str | None], *, encrypted: bool = False) -> bytes:
    """Synthetic test-only PDF, never represented as a research paper."""
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Synthetic ingestion fixture"})
    for text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        if text is not None:
            font = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
            })
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("test-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, data_dir=tmp_path / "data", max_upload_mb=1, max_pdf_pages=5)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as session:
        yield session


@pytest.fixture
def sample_pdf():
    return make_pdf(["PAGE ONE FACT: alpha evidence.", "PAGE TWO FACT: beta evidence."])


def upload(client, content: bytes, name: str = "test-fixture.pdf"):
    return client.post("/api/documents/upload", files={"file": (name, content, "application/pdf")})
