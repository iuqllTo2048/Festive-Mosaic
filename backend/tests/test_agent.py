import json
import time

import httpx
import pytest

from app.errors import IngestError
from app.schemas import AuditProposal, RequirementPlan
from conftest import make_pdf, upload
from test_query import install_transport


def install_agent(client, monkeypatch, judge, requirements=None):
    planned = requirements or [{"text": "核查目标事实", "search_query": "betazebra"}]
    def plan(question, budget):
        budget.take()
        return RequirementPlan.model_validate({"requirements": planned})
    calls = []
    def audit(question, requirements, hits, budget):
        budget.take()
        calls.append([hit.chunk.id for hit in hits])
        return judge(requirements, hits, len(calls), budget)
    monkeypatch.setattr(client.app.state.llm, "plan", plan)
    monkeypatch.setattr(client.app.state.llm, "audit", audit)
    return calls


def proposal(requirements, chunk=None, quote=None, status="supported", answer="有来源的测试事实。", repair="betazebra"):
    return AuditProposal.model_validate({"judgments": [{
        "requirement_id": requirement.id, "status": status, "explanation": "合成测试中的审计解释。",
        "answer": answer if status == "supported" else "", "repair_query": repair,
        "evidence": [{"chunk_id": chunk.id, "quote": quote or chunk.text[:160]}] if chunk else [],
    } for requirement in requirements]})


def ask(client, **overrides):
    return client.post("/api/query", json={"question": "alpha", "mode": "audited",
                                           "enable_graph_expansion": False, **overrides})


def test_planner_limits_and_format_retry(client, monkeypatch):
    upload(client, make_pdf(["Alpha evidence."]))
    calls = []
    def handler(request):
        calls.append(request)
        content = json.dumps({"requirements": [{"text": "需求", "search_query": "alpha"}] * 5})
        return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 0,
            "model": "test-model", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": content}}]})
    install_transport(monkeypatch, handler)
    result = ask(client).json()
    assert len(calls) == 2
    assert len(result["requirements"]) == 1
    assert result["stats"]["stop_reason"] == "llm_invalid_response"
    assert result["citations"] == []
    assert result["trace"][-1]["type"] == "stop"


@pytest.mark.parametrize("failure", ["quote", "unknown_chunk", "no_evidence", "unsupported_term", "unsupported_number"])
def test_fabricated_quote_never_supports_requirement(client, monkeypatch, failure):
    upload(client, make_pdf(["Alpha evidence is present in this source."]))
    def judge(requirements, hits, call, budget):
        candidate = hits[0].chunk
        if failure == "unknown_chunk":
            candidate = candidate.model_copy(update={"id": "invented_chunk"})
        return proposal(requirements, None if failure == "no_evidence" else candidate,
                        quote="This fabricated quotation cannot be found." if failure == "quote" else None,
                        answer="Alpha 与 ImaginaryBenchmarkVariant" if failure == "unsupported_term" else
                               "测量值为9999.5焦耳。" if failure == "unsupported_number" else "有来源的测试事实。",
                        repair="alpha")
    install_agent(client, monkeypatch, judge)
    result = ask(client).json()
    assert result["requirements"][0]["status"] == "insufficient"
    assert result["citations"] == []
    assert not any(edge["type"] == "supports" for edge in result["graph"]["edges"])
    assert all(not item["validated"] for item in result["evidence"])
    assert result["stats"]["repair_rounds"] == 1


@pytest.mark.parametrize("extra_definition", [False, True])
def test_repair_at_most_once_and_recovers(client, monkeypatch, extra_definition):
    upload(client, make_pdf(["Alpha source is unrelated to the target.", "Betazebra measured value is forty two."]))
    def judge(requirements, hits, call, budget):
        target = next((hit.chunk for hit in hits if "Betazebra" in hit.chunk.text), None)
        return proposal(requirements, target, status="supported" if target else "insufficient")
    planned = [{"text": "核查目标事实", "search_query": "betazebra"}]
    if extra_definition:
        planned.append({"text": "核查方法缩写的英文全称", "search_query": "alpha acronym"})
    calls = install_agent(client, monkeypatch, judge, requirements=planned)
    result = ask(client).json()
    assert len(calls) == 2
    assert result["stats"]["repair_rounds"] == 1
    assert result["stats"]["supported_requirements"] == 1
    assert result["stats"]["total_requirements"] == 1
    assert result["stats"]["display_coverage_ratio"] == 1
    assert result["stats"]["stop_reason"] == "covered_after_repair"
    assert result["citations"][0]["page"] == 2
    assert sum(item["type"] == "repair_start" for item in result["trace"]) == 1
    assert client.get(f"/api/runs/{result['run_id']}").json() == result


@pytest.mark.parametrize("enabled", [True, False])
def test_repair_failure_and_disabled_stop(client, monkeypatch, enabled):
    upload(client, make_pdf(["Alpha evidence for a different claim."]))
    calls = install_agent(client, monkeypatch, lambda requirements, hits, call, budget:
                          proposal(requirements, status="insufficient", repair="unfindablezzzx"))
    result = ask(client, enable_repair=enabled).json()
    assert len(calls) == 1
    assert result["stats"]["repair_rounds"] == int(enabled)
    assert result["stats"]["stop_reason"] == ("repair_exhausted" if enabled else "repair_disabled")
    assert result["citations"] == []
    if enabled:
        assert any(item["type"] == "repair_retrieve" and not item["node_ids"] for item in result["trace"])


def test_graph_edges_have_sources_and_shared_concept_path(client, monkeypatch):
    upload(client, make_pdf(["Alpha search uses HotpotQA as the named benchmark.",
                            "HotpotQA has a source-linked detail on the second page."]))
    install_agent(client, monkeypatch, lambda requirements, hits, call, budget:
                  proposal(requirements, next(hit.chunk for hit in hits if hit.chunk.page_number == 2)))
    result = ask(client, enable_graph_expansion=True).json()
    assert result["stats"]["graph_expanded_chunks"] == 1
    assert result["graph"]["concept_expansion_enabled"]
    assert result["stats"]["repair_rounds"] == 0
    graph = result["graph"]
    assert len(graph["nodes"]) <= 120
    nodes = {node["id"]: node for node in graph["nodes"]}
    evidence = {link["id"]: link for link in result["evidence"]}
    for edge in graph["edges"]:
        assert edge["source"] in nodes and edge["target"] in nodes
        source = edge["provenance"]
        chunk = client.app.state.store.get_chunk(source["chunk_id"])
        assert chunk and chunk.document_id == source["document_id"] and chunk.page_number == source["page"]
        if edge["type"] == "mentions":
            assert chunk.text[source["char_start"]:source["char_end"]] == source["term"]
        if edge["type"] == "supports":
            assert evidence[source["evidence_id"]]["validated"]
    with client.app.state.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM concept_mentions").fetchone()[0] == 2


@pytest.mark.parametrize("failure", ["request_budget", "deadline", "timeout", "wrong_ids"])
def test_budget_and_model_failures_stop_conservatively(client, monkeypatch, failure):
    upload(client, make_pdf(["Alpha evidence from a real test page."]))
    def judge(requirements, hits, call, budget):
        if failure == "timeout":
            raise IngestError("llm_timeout", "模拟上游超时。", 504)
        result = proposal(requirements, hits[0].chunk)
        if failure == "wrong_ids":
            result.judgments[0].requirement_id = "invented_requirement"
        return result
    install_agent(client, monkeypatch, judge)
    real_plan = client.app.state.llm.plan
    def constrained_plan(question, budget):
        result = real_plan(question, budget)
        if failure == "request_budget":
            budget.maximum = 1
        elif failure == "deadline":
            budget.deadline = time.monotonic() - 1
        return result
    monkeypatch.setattr(client.app.state.llm, "plan", constrained_plan)
    result = ask(client).json()
    assert result["status"] == "insufficient"
    assert result["stats"]["supported_requirements"] == 0
    assert result["stats"]["repair_rounds"] == 0
    assert result["citations"] == []
    assert result["trace"][-1]["type"] == "stop"
    assert any(item["type"] == "error" for item in result["trace"])


def test_supported_evidence_survives_repair_error(client, monkeypatch):
    upload(client, make_pdf(["Alpha measured fact can be located in this source."]))
    def judge(requirements, hits, call, budget):
        if call == 2:
            raise IngestError("llm_service_error", "模拟补检验证服务错误。", 502)
        result = proposal(requirements, hits[0].chunk, repair="alpha")
        result.judgments[1].status = "insufficient"
        result.judgments[1].answer = ""
        result.judgments[1].evidence = []
        return result
    install_agent(client, monkeypatch, judge, requirements=[
        {"text": "核对已知事实", "search_query": "alpha"}, {"text": "核对缺失的测量", "search_query": "alpha"},
    ])
    result = ask(client).json()
    assert [item["status"] for item in result["requirements"]] == ["supported", "insufficient"]
    assert result["stats"]["display_coverage_ratio"] == .5
    assert result["stats"]["repair_rounds"] == 1
    assert result["stats"]["stop_reason"] == "llm_service_error"
    assert len(result["citations"]) == 1
