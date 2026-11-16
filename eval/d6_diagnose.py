"""D6 diagnostics only. Production modules are imported unchanged.

Offline: uv run --locked python ../eval/d6_diagnose.py
Online: add --online (at most 6 full runs / 24 actual requests; cached runs reused).
All semantic labels are provisional until an independent human reviews them.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/tests")]
from pypdf import PdfReader
from pydantic import SecretStr
from app.config import Settings
from app.store import Store
from app.retrieve import retrieve, tokenize
from app.graph import extract_mentions, expand_shared_terms
from app.agent import run_audited_query
from app.query import run_query
from app.schemas import QueryRequest, RequirementPlan, AuditProposal
from app.llm import DeepSeekClient
from app.ingest import ingest_pdf
from app.errors import IngestError
from conftest import make_pdf

OUT = ROOT / "eval"
RESULTS = OUT / "d6_results.jsonl"
BASE = "602d42508a89f3eadeb5f6e73f3514a6d9ca2e73"
URLS = {"kg2rag": "https://aclanthology.org/2025.naacl-long.449/",
        "lightrag": "https://arxiv.org/abs/2410.05779v3", "paperqa2": "https://arxiv.org/abs/2409.13740v2"}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(kind, ident, **data):
    row = {"test": kind, "id": ident, "recorded_at": datetime.now(timezone.utc).isoformat(), **data}
    with RESULTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
    return row


def norm(text):
    return " ".join(text.split())


def definitions():
    # Candidate evidence chosen before retrieval scoring. No human labels are invented.
    full = ("kg2rag", 5, "In the fullwiki setting, it is required to identify useful knowledge from the entire 66,581 documents extracted from Wikipedia.")
    dist = ("kg2rag", 5, "In the distractor setting, a total of ten documents are provided as supporting ma- terials, including all useful knowledge as well as some irrelevant content.")
    latency = ("kg2rag", 13, "KG2RAG 25ms 2,300ms")
    low = ("lightrag", 2, "low-level retrieval, which focuses on precise information about specific entities and their relationships")
    high = ("lightrag", 2, "high-level retrieval, which encompasses broader topics and themes")
    precision = ("paperqa2", 3, "superhuman precision on this task (t(8.6) = 3.49, p = 0.0036)")
    accuracy = ("paperqa2", 3, "did not differ significantly from humans in accuracy (t(8.5) = −0.42, p = 0.66)")
    sources = ("paperqa2", 13, "This parameter was 5 in the top-performing Answer cutoff @ 5, but 15 for all other experiments.")
    table = ("kg2rag", 13, "LightRAG 0.248 0.170 0.289 GraphRAG 0.231 0.156 0.273 KG2RAG 0.419 0.303 0.451 Table 7: Comparison results on MuSiQue.")
    kg = ("kg2rag", 4, "spanning tree (MST) of each connected component")
    return [
        ("A01", "fact_numeric", ["kg2rag"], "In the fullwiki setting, how many Wikipedia documents are searched?", "候选范围66,581，需保留fullwiki条件", [full], False),
        ("A02", "fact_numeric", ["kg2rag"], "What average retrieval and generation time per query does KG2RAG report in Table 10?", "25ms检索、2,300ms生成，不是能耗", [latency], False),
        ("A03", "fact_numeric", ["paperqa2"], "What max_sources values were used for Answer cutoff @ 5 and other experiments?", "分别5和15，保留实验条件", [sources], False),
        ("A04", "multi_condition", ["kg2rag"], "Compare distractor and fullwiki settings: document counts and whether irrelevant supporting material is present.", "同时核查十篇/无关内容和66,581候选范围", [dist, full], False),
        ("A05", "multi_condition", ["paperqa2"], "How did PaperQA2 compare with humans in precision and accuracy, and were both differences statistically significant?", "precision显著；accuracy未显著不同，不能混淆", [precision, accuracy], False),
        ("A06", "cross_paper", list(URLS), "Can we conclude LightRAG outperforms KG2RAG on every retrieval task?", "仅有局部MuSiQue比较，普遍结论不足", [table], True),
        ("A07", "cross_paper", ["kg2rag", "lightrag"], "Compare LightRAG low-level and high-level retrieval with KG2RAG maximum spanning tree chunk organization.", "分别找两篇方法原文，不把结构差异推成排名", [low, high, kg], False),
        ("A08", "chinese_paraphrase", ["lightrag"], "这篇论文的低层级和高层级检索分别关注什么？", "具体实体关系与广泛主题；与A09同证据", [low, high], False),
        ("A09", "chinese_paraphrase", ["lightrag"], "How does the method look up fine grained items versus broad themes?", "同义改写，比较与原始dual-level术语召回差异", [low, high], False),
        ("A10", "unanswerable", ["kg2rag"], "Which dataset does KG2RAG use and what energy consumption in joules per query is measured?", "数据集部分可答，焦耳能耗需声明不足；时延仅作相关反例", [latency], True),
        ("A11", "unanswerable", ["paperqa2"], "What were PaperQA2's outcomes in a private clinical trial conducted in 2028?", "语料不能直接回答，不编造未来私人实验", [], True),
        ("A12", "negation_comparison_trap", ["paperqa2"], "Does PaperQA2 significantly outperform human annotators in accuracy rather than only precision?", "不得将precision显著改写成accuracy显著", [precision, accuracy], True),
    ]


def corpus():
    settings = Settings()
    store = Store(settings.resolved_data_dir)
    docs = {key: next(d for d in store.list_documents() if d.source_url == url) for key, url in URLS.items()}
    chunks = store.retrieval_chunks([d.id for d in docs.values()])
    readers = {key: PdfReader(store.pdf_path(d)) for key, d in docs.items()}
    for key, doc in docs.items():
        assert hashlib.sha256(store.pdf_path(doc).read_bytes()).hexdigest() == doc.sha256
    return settings, store, docs, chunks, readers


def offline():
    if RESULTS.exists():
        raise SystemExit("Offline results already exist; preserve them. Do not silently overwrite/relabel.")
    settings, store, docs, chunks, readers = corpus()
    save(OUT / "d6_baseline.json", {"baseline_commit": BASE, "date": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p) for p in ("fastapi", "rank-bm25", "pypdf", "openai")},
        "model": settings.deepseek_model, "max_tokens": settings.llm_max_tokens, "temperature": "not explicitly set",
        "thinking": "disabled", "seed": "not set", "budget": {"max_full_runs": 6, "max_actual_requests": 24, "max_reported_tokens": 50000, "max_wall_seconds": 300},
        "corpus": [{"paper_id": k, "document_id": d.id, "sha256": d.sha256, "pages": d.page_count, "chunks": d.chunk_count} for k, d in docs.items()],
        "human_independent_review": False, "production_code_modified": False})
    cases = []
    for ident, category, papers, question, needs, specs, abstain in definitions():
        refs = []
        for index, (paper, page, quote) in enumerate(specs):
            page_text = readers[paper].pages[page-1].extract_text() or ""
            candidates = [c for c in chunks if c.document_id == docs[paper].id and c.page_number == page and norm(quote) in norm(c.text)]
            assert norm(quote) in norm(page_text), f"Quote not found on PDF page: {ident}:{index}"
            assert candidates, f"Quote not fully contained in a chunk: {ident}:{index}"
            refs.append({"reference_id": f"{ident}_r{index+1}", "paper_id": paper, "document_id": docs[paper].id,
                "page": page, "chunk_id": candidates[0].id, "equivalent_chunk_ids": [c.id for c in candidates],
                "quote": quote, "pdf_page_quote_verified": True, "chunk_quote_verified": True,
                "role": "context_only_not_answer_evidence" if ident in {"A06", "A10"} else "candidate_support",
                "semantic_label": "provisional", "human_verified": False})
        case = {"id": ident, "category": category, "paper_ids": papers, "question": question, "reference_need": needs,
            "must_abstain_or_qualify": abstain, "human_verified": False, "label_status": "provisional", "references": refs}
        if not refs:
            case['reference_absence_reason']='No positive source for the requested private future trial; do not fabricate a quote. Abstention label remains provisional.'
        cases.append(case)
    save(OUT / "d6_cases.json", cases)
    for case in cases:
        scope = [c for c in chunks if c.document_id in {docs[p].id for p in case["paper_ids"]}]
        ranked = retrieve(case["question"], scope, 10)
        seeds = retrieve(case["question"], scope, 6)
        expanded, additions = expand_shared_terms(seeds, scope, extract_mentions(scope), 2)
        targets = [r for r in case["references"] if r["role"] == "candidate_support"]
        metrics = {}
        for label, hits in (("bm25_top10", ranked), ("native_6_plus_2", expanded)):
            row = {"returned": len(hits), "ordered_chunk_ids": [h.chunk.id for h in hits], "recall": {}}
            for k in (5, 10):
                found = {h.chunk.id for h in hits[:k]}
                row["recall"][str(k)] = (sum(bool(found.intersection(r["equivalent_chunk_ids"])) for r in targets)/len(targets)) if targets else None
            metrics[label] = row
        ranks = []
        all_ranked = retrieve(case["question"], scope, len(scope))
        for ref in targets:
            rank = next((i+1 for i,h in enumerate(all_ranked) if h.chunk.id in ref["equivalent_chunk_ids"]), None)
            target = store.get_chunk(ref["chunk_id"])
            overlap = sorted(set(tokenize(case["question"])) & set(tokenize(target.text)))
            ranks.append({"reference_id": ref["reference_id"], "rank": rank, "lexical_overlap": overlap,
                "failure_hypothesis": "lexical_no_overlap" if not overlap else "ranking_below_10" if rank and rank>10 else "within_top10"})
        record("A", case["id"], category=case["category"], formal_metrics=None, formal_reason="No independently human-verified semantic gold",
            exploratory=True, candidate_reference_count=len(targets), retrieval=metrics, target_ranks=ranks, expansion_additions=additions)
    # Direct inspection of production chunk boundaries; no changes to chunking.
    cut = []
    for c in chunks:
        paper = next(k for k,d in docs.items() if d.id == c.document_id)
        page = (readers[paper].pages[c.page_number-1].extract_text() or "").strip()
        if 0 < c.char_end < len(page) and page[c.char_end-1].isalnum() and page[c.char_end].isalnum():
            cut.append({"chunk_id": c.id, "page": c.page_number, "boundary": page[c.char_end-20:c.char_end+20]})
    record("A_boundary", "cuts", total_chunks=len(chunks), cuts_inside_alphanumeric_token=len(cut), examples=cut[:8])
    adversarial(settings)
    print("Offline A/B completed; all semantic references remain provisional. See eval/d6_results.jsonl", flush=True)


def adversarial(settings):
    completed = {json.loads(line)["id"] for line in RESULTS.read_text(encoding="utf-8").splitlines() if json.loads(line)["test"] == "B"} if RESULTS.exists() else set()
    fixtures = [
        ("B01", "non_entailment", "The instrument was installed in Room 4.", "设备已证明能够改善治疗效果。", "insufficient"),
        ("B02", "reversed_comparison", "Method A scored 80 and Method B scored 90 on Dataset X.", "Method A 高于 Method B，分数分别为80和90。", "insufficient"),
        ("B03", "negation_reversed", "The treatment did not improve survival in the trial.", "该治疗显著提高了试验中的存活率。", "insufficient"),
        ("B04", "condition_generalization", "In adults, treatment increased score from 10 to 20; children were not studied.", "治疗能使所有儿童的评分从10提高到20。", "insufficient"),
        ("B05", "latency_as_energy_Chinese", "Average latency per query is 42 milliseconds.", "每次查询能耗为42焦耳。", "insufficient"),
        ("B06", "valid_numeric_paraphrase", "Alpha observed forty two samples.", "观察了42个样本。", "supported"),
        ("B07", "latency_as_energy_English_control", "Average latency per query is 42 milliseconds.", "Measured energy is 42 joules.", "insufficient"),
        ("B08", "valid_literal_control", "Alpha observed 42 samples.", "观察了42个样本。", "supported"),
        ("B09", "fabricated_quote_control", "Alpha observed 42 samples.", "观察了42个样本。", "insufficient"),
    ]
    for ident, failure, source, answer, expected in fixtures:
        if ident in completed:
            continue
        # Windows sqlite objects may remain referenced until GC. Keep diagnostic
        # fixtures in the ignored local data dir; no destructive cleanup retries.
        directory = tempfile.mkdtemp(prefix="d6-", dir=settings.resolved_data_dir)
        if directory:
            local_settings = Settings(_env_file=None, data_dir=Path(directory), deepseek_api_key=SecretStr("fixture-not-real"))
            local_store = Store(Path(directory)); local_store.initialize()
            doc = ingest_pdf(make_pdf([source]), "synthetic-d6.pdf", local_store, local_settings).document
            chunk = local_store.retrieval_chunks([doc.id])[0]
            quote = source if ident != "B09" else "Alpha observed 99 samples."
            class FixedModel:
                def plan(self, question, budget):
                    budget.take()
                    return RequirementPlan(requirements=[{"text": "核查当前结论", "search_query": "Alpha"}])
                def audit(self, question, requirements, hits, budget):
                    budget.take()
                    return AuditProposal(judgments=[{"requirement_id": requirements[0].id, "status": "supported",
                        "answer": answer, "explanation": "固定夹具提出支持，交给现有保护逻辑检查。",
                        "evidence": [{"chunk_id": chunk.id, "quote": quote}], "repair_query": None}])
            # Only model output is controlled; retrieval, quote checks, graph and audit are unchanged.
            result = run_audited_query(QueryRequest(question=source, document_ids=[doc.id], mode="audited", enable_repair=False,
                enable_graph_expansion=False), local_store, local_settings, FixedModel())
            actual = result.requirements[0].status
            record("B", ident, fixture_type="synthetic_fixed_model_output", scenario=failure, expected_status=expected,
                expected_label_status="provisional_fixture_author", human_verified=False, actual_status=actual,
                expectation_matched=actual == expected, supports_edges=sum(e.type == "supports" for e in result.graph.edges),
                false_support_blocked=(actual != "supported") if expected == "insufficient" else None,
                quote_located=norm(quote) in norm(chunk.text), actual_api_requests=0, known_limitation=True,
                failure_layer="semantic_or_literal_guard" if actual != expected else None,
                source=source, proposed_answer=answer, proposed_quote=quote, raw_result=result.model_dump(mode="json"))


def online():
    """Observe SDK usage and plan/audit inputs without changing requests or decisions."""
    import openai
    from openai.resources.chat.completions import Completions
    settings, store, docs, chunks, readers = corpus()
    cases = json.loads((OUT / "d6_cases.json").read_text(encoding="utf-8"))
    existing = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    spent = sum(r.get("actual_requests", 0) for r in existing if r["test"] == "C")
    tokens = sum(r.get("total_tokens", 0) or 0 for r in existing if r["test"] == "C")
    done = {(r["id"], r.get("repair")) for r in existing if r["test"] == "C"}
    if any(r["test"] == "C_stop" for r in existing):
        raise SystemExit("Online stop recorded; inspect checkpoint and explicitly resume in a later session, no automatic retry.")
    started = time.monotonic()
    original_create = Completions.create
    for ident in ("A04", "A08", "A10"):
        case = next(c for c in cases if c["id"] == ident)
        for repair in (False, True):
            if (ident, repair) in done:
                continue
            if spent + 6 > 24 or tokens >= 50000 or time.monotonic()-started > 300:
                record("C_stop", "budget", actual_requests=spent, reported_tokens=tokens, reason="preset_budget_before_new_run")
                return
            calls, observations = [], []
            def observed_create(client, *args, **kwargs):
                tick = time.monotonic()
                receipt = {"model_requested": kwargs.get("model"), "max_tokens": kwargs.get("max_tokens")}
                calls.append(receipt)
                try:
                    response = original_create(client, *args, **kwargs)
                    receipt.update({"latency_ms": round((time.monotonic()-tick)*1000), "model_returned": response.model,
                        "usage": response.usage.model_dump(mode="json") if response.usage else None})
                    return response
                except Exception as error:
                    receipt["error_class"] = type(error).__name__
                    receipt["http_status"] = getattr(error, "status_code", None)
                    raise
            class ObservedModel(DeepSeekClient):
                def plan(self, question, budget):
                    result = super().plan(question, budget)
                    observations.append({"type": "plan", "result": result.model_dump(mode="json")})
                    return result
                def audit(self, question, requirements, hits, budget):
                    item = {"type": "audit", "requirements": [r.model_dump(mode="json") for r in requirements],
                        "hits": [{"chunk_id": h.chunk.id, "score": h.score} for h in hits]}
                    observations.append(item)
                    result = super().audit(question, requirements, hits, budget)
                    item["proposal"] = result.model_dump(mode="json")
                    return result
            with patch.object(Completions, "create", observed_create):
                result = run_query(QueryRequest(question=case["question"], document_ids=[docs[p].id for p in case["paper_ids"]],
                    mode="audited", enable_repair=repair, enable_graph_expansion=True), store, settings, ObservedModel(settings))
            actual = len(calls)
            usage = sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls)
            spent += actual; tokens += usage
            first, later = set(), set()
            repairing = False
            for event in result.trace:
                if event.type == "repair_start":
                    repairing = True
                if event.type in {"retrieve", "repair_retrieve", "graph_expand"}:
                    (later if repairing else first).update(event.node_ids)
            new = later - first
            accepted_repair = [e for e in result.evidence if e.round == 1 and e.validated]
            record("C", ident, repair=repair, pairing="non_strict_independent_plan", actual_requests=actual,
                total_tokens=usage if all(c.get("usage") for c in calls) else None, sdk_calls=calls, observations=observations,
                initial_evidence_ids=sorted(first), repair_evidence_ids=sorted(later), new_retrieved_chunk_ids=sorted(new),
                new_accepted_chunk_ids=sorted({e.chunk_id for e in accepted_repair} & new),
                reused_accepted_chunk_ids=sorted({e.chunk_id for e in accepted_repair} & first),
                reference_semantic_coverage=None, reference_reason="provisional and may not align with model plan",
                derivation_version="trace_stages_v2",
                raw_result=result.model_dump(mode="json"))
            save(OUT / "d6_checkpoint.json", {"completed_online": list(done | {(ident,repair)}), "actual_requests": spent,
                "reported_tokens": tokens, "last_run_id": result.run_id, "resume": "rerun --online; existing C rows reused"})
            print(f"{ident} repair={repair}: {result.stats.supported_requirements}/{result.stats.total_requirements}; calls={actual}; tokens={usage}; new accepted={len({e.chunk_id for e in accepted_repair}&new)}; stop={result.stats.stop_reason}", flush=True)
            if any(c.get("http_status") in (402, 429, 401, 403) or c.get("error_class") for c in calls) or any(t.type == "error" for t in result.trace):
                record("C_stop", "upstream", reason=result.stats.stop_reason, actual_requests=spent, reported_tokens=tokens)
                print("Stopped on first upstream/model anomaly; no automatic retry.", flush=True)
                return
            done.add((ident, repair))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--adversarial-only", action="store_true", help="Resume missing B cases without repeating A")
    parser.add_argument("--output", type=Path, default=OUT, help="Use a new directory to reproduce without overwriting preserved results")
    args = parser.parse_args()
    OUT = args.output.resolve()
    if not OUT.is_relative_to(ROOT):
        raise SystemExit("Diagnostic output must stay inside this workspace.")
    RESULTS = OUT / "d6_results.jsonl"
    OUT.mkdir(exist_ok=True, parents=True)
    if args.adversarial_only:
        adversarial(Settings())
    else:
        online() if args.online else offline()
