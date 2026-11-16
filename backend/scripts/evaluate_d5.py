"""Five paired live evaluations. Default verifies cached runs; --execute submits missing runs only.

Public-paper excerpts and questions go to the configured backend's DeepSeek service.
No automatic retries, no credential output. Run from backend/.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.agent import literal_claim_tokens_match
SOURCES = {
    "kg2rag": "https://aclanthology.org/2025.naacl-long.449/",
    "lightrag": "https://arxiv.org/abs/2410.05779v3",
    "paperqa2": "https://arxiv.org/abs/2409.13740v2",
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalized(text):
    return " ".join(text.split())


def verify(client, result, repair):
    """Check source integrity and bounds, not scientific truth or semantic entailment."""
    stats = result["stats"]
    assert result["audit_version"] == "quoted_claims_v2", "Cached run predates quote-level protection"
    requirements = {r["id"]: r for r in result["requirements"]}
    assert 1 <= len(requirements) <= 4
    supported = sum(r["status"] == "supported" for r in requirements.values())
    assert stats["supported_requirements"] == supported
    assert stats["total_requirements"] == len(requirements)
    assert stats["display_coverage_ratio"] == supported / len(requirements)
    assert 0 <= stats["repair_rounds"] <= int(repair)
    assert 0 < stats["llm_requests"] <= 6
    assert result["trace"][-1]["type"] == "stop"
    assert sum(t["type"] == "repair_start" for t in result["trace"]) == stats["repair_rounds"]
    assert [t["step"] for t in result["trace"]] == list(range(1, len(result["trace"]) + 1))
    graph = result["graph"]
    node_ids = {n["id"] for n in graph["nodes"]}
    edge_ids = {e["id"] for e in graph["edges"]}
    evidence = {e["id"]: e for e in result["evidence"]}
    chunks = {}

    def chunk(chunk_id):
        if chunk_id not in chunks:
            response = client.get(f"/api/chunks/{chunk_id}")
            response.raise_for_status()
            chunks[chunk_id] = response.json()
        return chunks[chunk_id]

    for edge in graph["edges"]:
        assert edge["source"] in node_ids and edge["target"] in node_ids
        ref = edge["provenance"]
        source = chunk(ref["chunk_id"])
        assert source["document_id"] == ref["document_id"] and source["page_number"] == ref["page"]
        if edge["type"] == "mentions":
            assert source["text"][ref["char_start"]:ref["char_end"]] == ref["term"]
        if edge["type"] == "supports":
            item = evidence[ref["evidence_id"]]
            assert item["validated"] and normalized(item["quote"]) in normalized(source["text"])
            requirement = requirements[edge["target"]]
            assert requirement["status"] == "supported" and item["id"] in requirement["evidence_ids"]
    for event in result["trace"]:
        assert set(event["node_ids"]) <= node_ids and set(event["edge_ids"]) <= edge_ids
    for citation in result["citations"]:
        source = chunk(citation["chunk_id"])
        assert normalized(citation["quote"]) in normalized(source["text"])
        assert citation["document_id"] == source["document_id"] and citation["page"] == source["page_number"]
        assert citation["pdf_url"].endswith(f"#page={citation['page']}")
        assert evidence[citation["evidence_id"]]["validated"]
    for requirement in requirements.values():
        if requirement["status"] == "supported":
            quotes = [evidence[eid]["quote"] for eid in requirement["evidence_ids"]]
            assert literal_claim_tokens_match(requirement["explanation"],
                [chunk(evidence[eid]["chunk_id"])["text"] for eid in requirement["evidence_ids"]])
            for paragraph in result["paragraphs"]:
                refs = [c for c in result["citations"] if c["id"] in paragraph["citation_ids"]]
                if any(c["evidence_id"] in requirement["evidence_ids"] for c in refs):
                    assert literal_claim_tokens_match(paragraph["text"], quotes)
    saved = client.get(f"/api/runs/{result['run_id']}")
    saved.raise_for_status()
    assert saved.json() == result
    return {
        "run_id": result["run_id"], "supported": supported, "requirements": len(requirements),
        "unresolved": len(requirements) - supported, "citations": len(result["citations"]),
        "duration_ms": stats["duration_ms"], "llm_requests": stats["llm_requests"],
        "repair_rounds": stats["repair_rounds"], "stop_reason": stats["stop_reason"],
        "source_integrity": "passed", "semantic_review": "see docs/D5_VERIFICATION.md; not an entailment proof",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Call models for missing cases only")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/d5")
    args = parser.parse_args()
    if urlparse(args.base_url).hostname not in {"127.0.0.1", "localhost"}:
        raise SystemExit("This evaluation accepts only the local backend.")
    cases = json.loads((ROOT / "samples/d5_questions.json").read_text(encoding="utf-8"))
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "real_api": True,
              "note": "Exploratory five-question sample; independent model plans may differ between paired runs. Not an accuracy benchmark or causal ablation.",
              "cases": []}
    with httpx.Client(base_url=args.base_url, timeout=115) as client:
        response = client.get("/api/documents")
        response.raise_for_status()
        documents = response.json()
        if args.execute and (len(documents) != 3 or {d["source_url"] for d in documents} != set(SOURCES.values())):
            raise SystemExit("Live evaluation expects exactly the three official public sources; other local papers must not enter its all-corpus case.")
        for case in cases:
            document_ids = None
            if case["paper"]:
                paper = next((d for d in documents if d["source_url"] == SOURCES[case["paper"]]), None)
                if paper is None:
                    raise SystemExit(f"Import official source first: {case['paper']}")
                document_ids = [paper["id"]]
            row = {**case, "runs": {}}
            for repair in (False, True):
                label = "repair_on" if repair else "repair_off"
                path = args.output / f"{case['id']}-{label}.json"
                if path.exists():
                    receipt = json.loads(path.read_text(encoding="utf-8"))
                    assert receipt["request"] == {"question": case["question"], "document_ids": document_ids,
                        "mode": "audited", "enable_repair": repair, "enable_graph_expansion": True}
                    result = receipt["result"]
                else:
                    if not args.execute:
                        raise SystemExit(f"Missing {path.name}; use --execute to submit paid requests.")
                    payload = {"question": case["question"], "document_ids": document_ids,
                               "mode": "audited", "enable_repair": repair, "enable_graph_expansion": True}
                    print(f"Submitting {case['id']} {label}", flush=True)
                    response = client.post("/api/query", json=payload)
                    if response.is_error:
                        raise SystemExit(f"{case['id']} {label}: {response.json().get('error', {}).get('code', response.status_code)}; no automatic retry")
                    result = response.json()
                    write_json(path, {"executed_at": datetime.now(timezone.utc).isoformat(), "request": payload, "result": result})
                row["runs"][label] = verify(client, result, repair)
                stats = row["runs"][label]
                print(f"{case['id']} {label}: {stats['supported']}/{stats['requirements']} supported; {stats['citations']} citations; {stats['llm_requests']} requests; {stats['duration_ms']} ms; {stats['stop_reason']}", flush=True)
            report["cases"].append(row)
            write_json(args.output / "comparison.json", report)
        empty_path = args.output / "E5-basic.json"
        if empty_path.exists():
            empty = json.loads(empty_path.read_text(encoding="utf-8"))["result"]
        else:
            if not args.execute:
                raise SystemExit("Missing E5-basic.json; --execute also runs the zero-match basic check.")
            payload = {"question": "zzzxquantumunfindable", "mode": "basic"}
            response = client.post("/api/query", json=payload)
            response.raise_for_status()
            empty = response.json()
            write_json(empty_path, {"request": payload, "result": empty})
        assert empty["status"] == "insufficient" and empty["citations"] == []
        assert empty["stats"]["retrieved_chunks"] == 0 and empty["stats"]["llm_requests"] == 0
        assert client.get(f"/api/runs/{empty['run_id']}").json() == empty
        report["empty_lexical_basic"] = {"run_id": empty["run_id"], "citations": 0, "llm_requests": 0, "verified": True}
        write_json(args.output / "comparison.json", report)
    print(f"Report: {(args.output / 'comparison.json').resolve()}", flush=True)


if __name__ == "__main__":
    main()
