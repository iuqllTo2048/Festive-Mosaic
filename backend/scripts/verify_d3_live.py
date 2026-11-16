"""Real D3 audit and bounded-repair check; --run-id reads a saved run without model calls."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

QUESTION = "Which evaluation dataset does KG2RAG use, and what measured energy consumption in joules per query does the paper report? Cite evidence for each; if a measurement is not supported by the excerpts, say it is unknown."


def normalized(text):
    return " ".join(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("../artifacts/d3/live-check.json"))
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=115) as client:
        if args.run_id:
            response = client.get(f"/api/runs/{args.run_id}")
        else:
            documents = client.get("/api/documents").json()
            paper = next((item for item in documents if item["source_url"] == "https://aclanthology.org/2025.naacl-long.449/"), None)
            if paper is None:
                raise SystemExit("Import the official KG2RAG PDF first.")
            response = client.post("/api/query", json={"question": QUESTION, "document_ids": [paper["id"]],
                "mode": "audited", "enable_repair": True, "enable_graph_expansion": True})
        if response.is_error:
            raise SystemExit(f"Query failed: {response.json().get('error', {}).get('code', response.status_code)}")
        result = response.json()
        assert result["mode"] == "audited"
        assert result["audit_version"] == "literal_claims_v1", "Run predates claim-token validation"
        requirements = {item["id"]: item for item in result["requirements"]}
        assert 1 <= len(requirements) <= 4
        supported = sum(item["status"] == "supported" for item in requirements.values())
        stats = result["stats"]
        assert stats["total_requirements"] == len(requirements)
        assert stats["supported_requirements"] == supported
        assert stats["display_coverage_ratio"] == supported / len(requirements)
        assert stats["repair_rounds"] == 1, "This check expects a real missing-evidence repair round"
        assert 0 < stats["llm_requests"] <= 6
        assert any(item["status"] == "insufficient" for item in requirements.values()), "Missing measurement must remain unresolved"
        assert result["insufficient"] and stats["stop_reason"] == "repair_exhausted"
        trace = result["trace"]
        assert [item["step"] for item in trace] == list(range(1, len(trace) + 1))
        assert sum(item["type"] == "repair_start" for item in trace) == 1
        assert trace[-1]["type"] == "stop"
        graph = result["graph"]
        assert len(graph["nodes"]) <= 120
        nodes = {item["id"] for item in graph["nodes"]}
        edges = {item["id"] for item in graph["edges"]}
        evidence = {item["id"]: item for item in result["evidence"]}
        chunks = {}
        def chunk(chunk_id):
            if chunk_id not in chunks:
                response = client.get(f"/api/chunks/{chunk_id}")
                response.raise_for_status()
                chunks[chunk_id] = response.json()
            return chunks[chunk_id]
        for edge in graph["edges"]:
            assert edge["source"] in nodes and edge["target"] in nodes
            provenance = edge["provenance"]
            source = chunk(provenance["chunk_id"])
            assert source["document_id"] == provenance["document_id"] and source["page_number"] == provenance["page"]
            if edge["type"] == "mentions":
                assert source["text"][provenance["char_start"]:provenance["char_end"]] == provenance["term"]
            if edge["type"] == "supports":
                link = evidence[provenance["evidence_id"]]
                requirement = requirements[edge["target"]]
                assert link["validated"] and requirement["status"] == "supported"
                assert link["id"] in requirement["evidence_ids"]
                assert normalized(link["quote"]) in normalized(source["text"])
        for item in trace:
            assert set(item["node_ids"]) <= nodes
            assert set(item["edge_ids"]) <= edges
        for citation in result["citations"]:
            source = chunk(citation["chunk_id"])
            assert normalized(citation["quote"]) in normalized(source["text"])
            assert citation["page"] == source["page_number"]
            assert evidence[citation["evidence_id"]]["validated"]
        assert client.get(f"/api/runs/{result['run_id']}").json() == result
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "real_api": True,
                  "verification": {"one_repair_round": "passed", "unresolved_measurement": "passed",
                    "coverage_from_requirements": "passed", "graph_provenance": "passed",
                    "quote_and_page_mapping": "passed", "trace_references": "passed", "persisted_run": "passed"},
                  "result": result}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Run ID: {result['run_id']}")
        print(f"Supported: {supported}/{len(requirements)}; repair rounds: {stats['repair_rounds']}; requests: {stats['llm_requests']}")
        print(f"Graph: {len(nodes)} nodes, {len(edges)} edges; expanded chunks: {stats['graph_expanded_chunks']}")
        print(f"Stop: {stats['stop_reason']}; duration: {stats['duration_ms']} ms")
        print(f"Report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
