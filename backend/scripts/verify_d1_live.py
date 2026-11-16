"""Check the running D1 API with real, locally imported PDFs (no paid API).

From backend/: uv run python scripts/verify_d1_live.py --import-seeds
PDF bytes and source text are not included in the saved report.
"""
import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pypdf import PdfReader


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--import-seeds", action="store_true", help="Download the 3 manifest papers to the local data directory")
    parser.add_argument("--output", type=Path, default=Path("../artifacts/d1/live-check.json"))
    args = parser.parse_args()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "health": {}, "seed_results": [], "documents": []}
    with httpx.Client(base_url=args.base_url, timeout=120) as client:
        response = client.get("/api/health")
        response.raise_for_status()
        report["health"] = response.json()
        if args.import_seeds:
            for paper in client.get("/api/papers").json():
                response = client.post("/api/documents/seed", json={"paper_ids": [paper["id"]]})
                response.raise_for_status()
                for result in response.json():
                    report["seed_results"].append({
                        "paper_id": result["paper_id"], "status": result["status"], "error": result["error"],
                    })
                    print(f"{result['paper_id']}: {result['status']}", flush=True)
        response = client.get("/api/documents")
        response.raise_for_status()
        documents = response.json()
        if not documents:
            raise RuntimeError("No real PDF is available. Import or upload a paper first.")
        for document in documents:
            response = client.get(document["pdf_url"])
            response.raise_for_status()
            content = response.content
            assert hashlib.sha256(content).hexdigest() == document["sha256"], "Original PDF hash mismatch"
            reader = PdfReader(io.BytesIO(content))
            assert len(reader.pages) == document["page_count"], "Page count mismatch"
            page_text = {number: (page.extract_text() or "").strip() for number, page in enumerate(reader.pages, start=1)}
            chunks = []
            while len(chunks) < document["chunk_count"]:
                response = client.get(f"/api/documents/{document['id']}/chunks", params={"offset": len(chunks), "limit": 100})
                response.raise_for_status()
                batch = response.json()["items"]
                assert batch, "Missing chunks"
                chunks.extend(batch)
            assert len(chunks) == document["chunk_count"]
            for chunk in chunks:
                original = page_text[chunk["page_number"]]
                assert original[chunk["char_start"]:chunk["char_end"]] == chunk["text"], "Chunk does not match source page"
            response = client.post("/api/documents/upload", files={
                "file": ("real-paper-reupload.pdf", content, "application/pdf"),
            })
            response.raise_for_status()
            assert response.json()["duplicate"] is True, "Real PDF duplicate upload not detected"
            assert response.json()["document"]["id"] == document["id"]
            report["documents"].append({
                "title": document["title"], "document_id": document["id"], "page_count": len(reader.pages),
                "verified_chunks": len(chunks), "sha256": document["sha256"],
                "source_url": document["source_url"], "source_pdf_url": document["source_pdf_url"],
                "retrieved_at": document["retrieved_at"], "warnings": document["warnings"],
                "duplicate_upload": "passed", "pdf_hash": "passed", "page_and_text_mapping": "passed",
            })
            print(f"Verified: {document['title']} / {len(reader.pages)} pages / {len(chunks)} chunks", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
