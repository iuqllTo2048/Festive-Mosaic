import httpx
import pytest

from app import seed
from conftest import upload


def test_health_and_empty_library(client):
    assert client.get("/api/health").json() == {
        "status": "ok", "stage": "D1", "max_upload_mb": 1, "max_pdf_pages": 5,
    }
    assert client.get("/api/documents").json() == []


def test_chunk_pagination_and_invalid_page(client, sample_pdf):
    document = upload(client, sample_pdf).json()["document"]
    base = f"/api/documents/{document['id']}/chunks"
    result = client.get(base + "?offset=1&limit=1").json()
    assert result["total"] == 2
    assert result["items"][0]["page_number"] == 2
    assert client.get(base + "?page=3").status_code == 404
    assert client.get(base + "?page=0").status_code == 422
    assert client.get(base + "?limit=1000").status_code == 422
    assert client.get("/api/documents/missing/chunks").status_code == 404


def test_missing_upload_has_readable_error(client):
    result = client.post("/api/documents/upload")
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "invalid_request"


def test_missing_original_pdf_is_explicit(client, sample_pdf):
    document = upload(client, sample_pdf).json()["document"]
    client.app.state.store.pdf_path(client.app.state.store.get_document(document["id"])).unlink()
    assert client.get(document["pdf_url"]).status_code == 404
    assert upload(client, sample_pdf).status_code == 409


def test_manifest_has_three_real_official_sources(client):
    papers = client.get("/api/papers").json()
    assert {paper["id"] for paper in papers} == {"kg2rag", "lightrag", "paperqa2"}
    assert all(paper["source_url"].startswith("https://") and paper["authors"] for paper in papers)
    assert client.get("/api/documents").json() == []
    assert client.post("/api/documents/seed", json={"paper_ids": ["https://localhost/private"]}).status_code == 400


def patch_download(monkeypatch, handler):
    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(seed.httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))


def test_seed_download_import_and_dedup(client, sample_pdf, monkeypatch):
    patch_download(monkeypatch, lambda request: httpx.Response(200, content=sample_pdf))
    first = client.post("/api/documents/seed", json={"paper_ids": ["kg2rag"]}).json()[0]
    assert first["status"] == "imported"
    assert first["document"]["source_url"] == "https://aclanthology.org/2025.naacl-long.449/"
    assert first["document"]["authors"][0] == "Xiangrong Zhu"
    assert first["document"]["created_at"]
    assert first["document"]["retrieved_at"]
    assert first["document"]["source_pdf_url"] == "https://aclanthology.org/2025.naacl-long.449.pdf"
    second = client.post("/api/documents/seed", json={"paper_ids": ["kg2rag"]}).json()[0]
    assert second["status"] == "duplicate"


def test_official_download_enriches_existing_upload(client, sample_pdf, monkeypatch):
    uploaded = upload(client, sample_pdf).json()["document"]
    assert uploaded["source_url"] is None
    patch_download(monkeypatch, lambda request: httpx.Response(200, content=sample_pdf))
    result = client.post("/api/documents/seed", json={"paper_ids": ["kg2rag"]}).json()[0]
    assert result["status"] == "duplicate"
    assert result["document"]["id"] == uploaded["id"]
    assert result["document"]["retrieved_at"]
    assert client.get("/api/documents").json()[0]["source_pdf_url"]


@pytest.mark.parametrize("failure", ["timeout", "http_error", "html", "too_large"])
def test_seed_failure_is_honest_and_has_manual_source(client, monkeypatch, failure):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("test timeout")
        if failure == "http_error":
            return httpx.Response(503)
        if failure == "html":
            return httpx.Response(200, content=b"<html>blocked</html>")
        return httpx.Response(200, content=b"%PDF-" + b"0" * 1024 * 1024)
    patch_download(monkeypatch, handler)
    result = client.post("/api/documents/seed", json={"paper_ids": ["kg2rag"]}).json()[0]
    assert result["status"] == "failed"
    assert result["document"] is None
    assert result["error"]["message"]
    assert result["manual_url"] == "https://aclanthology.org/2025.naacl-long.449/"
    assert client.get("/api/documents").json() == []
