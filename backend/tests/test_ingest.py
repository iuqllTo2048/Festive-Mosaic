import sqlite3

import pytest
from pypdf import PageObject

from app.ingest import CHUNK_OVERLAP, CHUNK_SIZE
from app.main import create_app
from conftest import make_pdf, upload


def test_pdf_ingest_pages(client, sample_pdf):
    result = upload(client, sample_pdf)
    assert result.status_code == 200
    document = result.json()["document"]
    assert document["page_count"] == 2
    assert document["chunk_count"] == 2
    assert document["ingest_status"] == "ready"
    chunks = client.get(f"/api/documents/{document['id']}/chunks").json()["items"]
    assert [(chunk["page_number"], chunk["text"]) for chunk in chunks] == [
        (1, "PAGE ONE FACT: alpha evidence."), (2, "PAGE TWO FACT: beta evidence.")
    ]
    assert client.get(document["pdf_url"]).content == sample_pdf
    assert client.get(document["pdf_url"]).headers["content-type"] == "application/pdf"


def test_duplicate_upload_sha256(client, sample_pdf):
    first = upload(client, sample_pdf).json()
    second = upload(client, sample_pdf, "renamed.pdf").json()
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert first["document"]["id"] == second["document"]["id"]
    assert len(client.get("/api/documents").json()) == 1
    chunks = client.get(f"/api/documents/{first['document']['id']}/chunks").json()
    assert chunks["total"] == 2


def test_chunks_overlap_without_crossing_pages(client):
    text = "Evidence phrase " * 140
    document = upload(client, make_pdf([text, "SECOND PAGE."])).json()["document"]
    chunks = client.get(f"/api/documents/{document['id']}/chunks?page=1").json()["items"]
    reconstructed = chunks[0]["text"]
    for previous, chunk in zip(chunks, chunks[1:]):
        assert previous["char_end"] - chunk["char_start"] == CHUNK_OVERLAP
        assert previous["text"][-CHUNK_OVERLAP:] == chunk["text"][:CHUNK_OVERLAP]
        reconstructed += chunk["text"][CHUNK_OVERLAP:]
    assert reconstructed == text.strip()
    assert all(chunk["page_number"] == 1 and len(chunk["text"]) <= CHUNK_SIZE for chunk in chunks)
    page_two = client.get(f"/api/documents/{document['id']}/chunks?page=2").json()["items"]
    assert page_two[0]["text"] == "SECOND PAGE."


def test_empty_pages_are_reported_without_changing_page_numbers(client):
    document = upload(client, make_pdf(["First page.", None, "Third page."])).json()["document"]
    assert document["page_count"] == 3
    assert document["ingest_status"] == "ready_with_warnings"
    assert "第 2 页" in document["warnings"][0]
    chunks = client.get(f"/api/documents/{document['id']}/chunks").json()["items"]
    assert [chunk["page_number"] for chunk in chunks] == [1, 3]
    assert client.get(f"/api/documents/{document['id']}/chunks?page=2").json()["total"] == 0


@pytest.mark.parametrize(("name", "content", "status", "code"), [
    ("empty.pdf", b"", 400, "empty_file"),
    ("text.txt", b"text", 415, "invalid_file_type"),
    ("fake.pdf", b"<html>not a PDF</html>", 422, "invalid_pdf"),
    ("broken.pdf", b"%PDF-1.7\ncorrupted", 422, "invalid_pdf"),
    ("big.pdf", b"%PDF-" + b"0" * 1024 * 1024, 413, "file_too_large"),
])
def test_invalid_uploads_do_not_create_records(client, name, content, status, code):
    result = upload(client, content, name)
    assert result.status_code == status
    assert result.json()["error"]["code"] == code
    assert client.get("/api/documents").json() == []
    assert list(client.app.state.store.pdf_dir.iterdir()) == []


def test_no_text_pdf_has_explicit_ocr_error(client):
    result = upload(client, make_pdf([None, None]))
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "no_extractable_text"
    assert "OCR" in result.json()["error"]["message"]


def test_encrypted_pdf_is_rejected(client):
    result = upload(client, make_pdf(["Secret"], encrypted=True))
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "encrypted_pdf"


def test_page_limit_is_enforced(client):
    result = upload(client, make_pdf(["text"] * 6))
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "too_many_pages"


def test_page_parse_failure_is_not_silently_skipped(client, monkeypatch):
    def broken_extract(self):
        raise ValueError("test page failure")
    monkeypatch.setattr(PageObject, "extract_text", broken_extract)
    result = upload(client, make_pdf(["Text."]))
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "page_parse_failed"
    assert client.get("/api/documents").json() == []


def test_filename_never_controls_disk_path(client, sample_pdf):
    document = upload(client, sample_pdf, "..\\..\\unsafe.pdf").json()["document"]
    assert document["original_filename"] == "unsafe.pdf"
    pdf = client.app.state.store.pdf_path(client.app.state.store.get_document(document["id"]))
    assert pdf.name == document["sha256"] + ".pdf"
    assert pdf.parent == client.app.state.store.pdf_dir
    assert client.get("/api/documents/not-a-real-document/pdf").status_code == 404


def test_storage_survives_restart(client, settings, sample_pdf):
    from fastapi.testclient import TestClient
    document = upload(client, sample_pdf).json()["document"]
    before = client.get(f"/api/documents/{document['id']}/chunks").json()
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get("/api/documents").json() == [document]
        assert restarted.get(f"/api/documents/{document['id']}/chunks").json() == before


def test_save_failure_cleans_up_pdf(client, sample_pdf, monkeypatch):
    def broken_save(document, chunks):
        raise sqlite3.OperationalError("simulated database error")
    monkeypatch.setattr(client.app.state.store, "save", broken_save)
    with pytest.raises(sqlite3.OperationalError):
        upload(client, sample_pdf)
    assert list(client.app.state.store.pdf_dir.iterdir()) == []
    assert client.get("/api/documents").json() == []
