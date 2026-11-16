"""Verify one real KG2RAG question. --run-id checks an existing UI run without another LLM call.

Run from backend/: uv run python scripts/verify_d2_live.py
Only imported public-paper excerpts are sent to DeepSeek. No credential is printed or saved.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

QUESTION = "Which benchmark dataset and its variants were used to evaluate KG2RAG? Answer only from the paper and give source quotes."


def normalize(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path, default=Path("../artifacts/d2/live-check.json"))
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=115) as client:
        if args.run_id:
            response = client.get(f"/api/runs/{args.run_id}")
        else:
            response = client.get("/api/documents")
            response.raise_for_status()
            documents = response.json()
            paper = next((doc for doc in documents if doc["source_url"] == "https://aclanthology.org/2025.naacl-long.449/"), None)
            if paper is None:
                raise RuntimeError("Import the official KG2RAG PDF before running this check.")
            response = client.post("/api/query", json={"question": QUESTION, "document_ids": [paper["id"]]})
        if response.is_error:
            error = response.json().get("error", {})
            raise SystemExit(f"Query failed: {error.get('code', response.status_code)}")
        result = response.json()
        assert result["status"] == "answered" and result["citations"], "No source-backed answer"
        assert "hotpotqa" in result["answer"].lower(), "Expected benchmark dataset missing from answer"
        assert result["stats"]["llm_requests"] in (1, 2)
        for citation in result["citations"]:
            response = client.get(f"/api/chunks/{citation['chunk_id']}")
            response.raise_for_status()
            chunk = response.json()
            assert normalize(citation["quote"]) in normalize(chunk["text"])
            assert chunk["document_id"] == citation["document_id"]
            assert chunk["page_number"] == citation["page"]
            assert citation["pdf_url"].endswith(f"#page={citation['page']}")
        assert client.get(f"/api/runs/{result['run_id']}").json() == result
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "real_api": True,
                  "verification": {"expected_hotpotqa_answer": "passed", "quote_in_chunk": "passed",
                                   "page_mapping": "passed", "persisted_run": "passed"},
                  "result": result}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Real API verified: {len(result['citations'])} citations, {result['stats']['llm_requests']} requests, {result['stats']['duration_ms']} ms")
        print(f"Run ID: {result['run_id']}")
        print(f"Report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
