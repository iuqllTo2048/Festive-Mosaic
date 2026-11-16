import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app import llm as llm_module
from app.errors import IngestError
from app.llm import DeepSeekClient
from app.main import create_app
from app.retrieve import retrieve
from app.schemas import ProposedAnswer
from conftest import make_pdf, upload


def stub_answer(client, monkeypatch, *, quote="PAGE TWO FACT: beta evidence.", chunk_id=None, text="第二页记录了 beta evidence。"):
    document = upload(client, make_pdf(["PAGE ONE FACT: alpha evidence.", "PAGE TWO FACT: beta evidence."])).json()["document"]
    chunk = client.get(f"/api/documents/{document['id']}/chunks?page=2").json()["items"][0]
    proposed = ProposedAnswer.model_validate({"paragraphs": [{"text": text, "citations": [
        {"chunk_id": chunk_id or chunk["id"], "quote": quote}
    ]}], "insufficient": []})
    monkeypatch.setattr(client.app.state.llm, "answer", lambda question, hits: (proposed, 1))
    return document, chunk


def test_retrieve_known_phrase(client, sample_pdf):
    upload(client, sample_pdf)
    hits = retrieve("beta evidence", client.app.state.store.retrieval_chunks(None), 1)
    assert hits[0].chunk.page_number == 2
    assert "beta evidence" in hits[0].chunk.text


def test_answer_citation_mapping_persisted(client, settings, monkeypatch):
    document, chunk = stub_answer(client, monkeypatch)
    response = client.post("/api/query", json={"question": "beta evidence"})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "answered"
    assert result["answer"].endswith("[1]")
    citation = result["citations"][0]
    assert (citation["chunk_id"], citation["document_id"], citation["page"]) == (chunk["id"], document["id"], 2)
    assert citation["pdf_url"].endswith("#page=2")
    assert client.get(f"/api/chunks/{chunk['id']}").json() == chunk
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(f"/api/runs/{result['run_id']}").json() == result


def test_no_evidence_no_citation(client, sample_pdf, monkeypatch):
    upload(client, sample_pdf)
    def should_not_call(*args):
        pytest.fail("LLM must not run without retrieved evidence")
    monkeypatch.setattr(client.app.state.llm, "answer", should_not_call)
    result = client.post("/api/query", json={"question": "zzzxquantumunfindable"}).json()
    assert result["citations"] == []
    assert result["status"] == "insufficient"
    assert result["stats"]["llm_requests"] == 0


@pytest.mark.parametrize(("quote", "chunk_id", "text"), [
    ("Fabricated quotation missing from the PDF.", None, "假的回答"),
    ("PAGE TWO FACT: beta evidence.", "unknown_chunk", "假的来源"),
    ("PAGE TWO FACT: beta evidence.", None, "不存在的引用 [99]"),
])
def test_invalid_source_never_becomes_citation(client, monkeypatch, quote, chunk_id, text):
    stub_answer(client, monkeypatch, quote=quote, chunk_id=chunk_id, text=text)
    result = client.post("/api/query", json={"question": "beta evidence"}).json()
    assert result["status"] == "insufficient"
    assert result["paragraphs"] == []
    assert result["citations"] == []


def test_whitespace_normalized_quote_is_valid(client, monkeypatch):
    stub_answer(client, monkeypatch, quote="PAGE TWO FACT:  beta\nevidence.")
    result = client.post("/api/query", json={"question": "beta evidence"}).json()
    assert result["status"] == "answered"


def test_scope_excludes_other_document(client):
    first = upload(client, make_pdf(["Alpha-only evidence."])).json()["document"]
    upload(client, make_pdf(["Betazebra-only evidence."]))
    result = client.post("/api/query", json={"question": "betazebra", "document_ids": [first["id"]]}).json()
    assert result["citations"] == []
    assert result["stats"]["retrieved_chunks"] == 0


def test_missing_key_is_honest(settings, sample_pdf):
    settings = settings.model_copy(update={"deepseek_api_key": llm_module.Settings.model_fields["deepseek_api_key"].default})
    with TestClient(create_app(settings)) as session:
        upload(session, sample_pdf)
        assert session.get("/api/health").json()["llm_configured"] is False
        result = session.post("/api/query", json={"question": "beta evidence"})
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "llm_not_configured"
        assert "test-only-not-a-real-key" not in result.text


def test_request_bounds_and_empty_library(client):
    assert client.post("/api/query", json={"question": "beta"}).status_code == 400
    assert client.post("/api/query", json={"question": " "}).status_code == 400
    assert client.post("/api/query", json={"question": "x" * 2001}).status_code == 422
    assert client.post("/api/query", json={"question": "beta", "top_k": 9}).status_code == 422
    assert client.post("/api/query", json={"question": "beta", "document_ids": ["missing"]}).status_code == 404
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/chunks/missing").status_code == 404


def install_transport(monkeypatch, handler):
    original = llm_module.openai.OpenAI
    monkeypatch.setattr(llm_module.openai, "OpenAI", lambda **kwargs: original(
        **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ))


@pytest.mark.parametrize(("failure", "expected"), [
    ("timeout", "llm_timeout"), (401, "llm_auth_failed"), (429, "llm_rate_limited"),
    (402, "llm_service_error"), (500, "llm_service_error"),
])
def test_llm_failure_has_no_fake_answer_or_secret(settings, monkeypatch, failure, expected):
    calls = []
    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(failure, json={"error": {"message": "test-only-not-a-real-key", "type": "error"}})
    install_transport(monkeypatch, handler)
    with pytest.raises(IngestError) as caught:
        DeepSeekClient(settings).answer("test", [])
    assert caught.value.code == expected
    assert "test-only-not-a-real-key" not in caught.value.message
    assert len(calls) == 1


def test_structured_output_retries_once(settings, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 0,
            "model": "test-model", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "not JSON"}}]})
    install_transport(monkeypatch, handler)
    with pytest.raises(IngestError) as caught:
        DeepSeekClient(settings).answer("test", [])
    assert caught.value.code == "llm_invalid_response"
    assert len(calls) == 2


def test_valid_json_after_one_format_retry(settings, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert body["thinking"]["type"] == "disabled"
        return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 0,
            "model": "test-model", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": " " if len(calls) == 1 else '{"paragraphs":[],"insufficient":["缺证据"]}'}}]})
    install_transport(monkeypatch, handler)
    result, requests = DeepSeekClient(settings).answer("test", [])
    assert requests == 2 and not result.paragraphs
