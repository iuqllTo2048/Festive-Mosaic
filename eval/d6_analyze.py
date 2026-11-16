"""Recompute D6 derived measurements from immutable raw results. Never calls a model."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from d6_diagnose import OUT, RESULTS, save, record, corpus, norm
from app.retrieve import retrieve


def main():
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    cases = {c["id"]: c for c in json.loads((OUT / "d6_cases.json").read_text(encoding="utf-8"))}
    retrieval = [r for r in rows if r["test"] == "A" and r["candidate_reference_count"]]
    summary = {"all_semantic_labels": "provisional", "human_verified_cases": 0,
        "formal_evidence_recall": None, "formal_reason": "No independently human-verified semantic reference",
        "retrieval": {}, "categories": {}, "online": []}
    for method in ("bm25_top10", "native_6_plus_2"):
        metrics = {}
        for k in ("5", "10"):
            total = sum(r["candidate_reference_count"] for r in retrieval)
            found = sum(round(r["retrieval"][method]["recall"][k]*r["candidate_reference_count"]) for r in retrieval)
            metrics[k] = {"hit_references": found, "candidate_references": total, "micro": found/total,
                "macro": sum(r["retrieval"][method]["recall"][k] for r in retrieval)/len(retrieval),
                "cases": len(retrieval), "exploratory_only": True}
        summary["retrieval"][method] = metrics
    groups = defaultdict(list)
    for r in retrieval:
        groups[r["category"]].append(r)
    for category, group in groups.items():
        summary["categories"][category] = {"cases": len(group), "bm25_5_macro":sum(r["retrieval"]["bm25_top10"]["recall"]["5"] for r in group)/len(group),
            "bm25_10_macro":sum(r["retrieval"]["bm25_top10"]["recall"]["10"] for r in group)/len(group),
            "expansion_10_macro":sum(r["retrieval"]["native_6_plus_2"]["recall"]["10"] for r in group)/len(group)}
    adversarial = [r for r in rows if r["test"] == "B"]
    summary["adversarial"] = {"fixture_cases":len(adversarial),
        "provisional_false_support_count":sum(r["expected_status"]=="insufficient" and r["actual_status"]=="supported" for r in adversarial),
        "provisional_false_rejection_count":sum(r["expected_status"]=="supported" and r["actual_status"]=="insufficient" for r in adversarial),
        "expected_negative_count":sum(r["expected_status"]=="insufficient" for r in adversarial),
        "api_requests":0,"note":"Controlled upstream errors; not a frequency estimate for real model outputs"}
    total_refs = sum(r["candidate_reference_count"] for r in retrieval)
    bm8 = sum(sum(bool(set(r["retrieval"]["bm25_top10"]["ordered_chunk_ids"][:8]).intersection(ref["equivalent_chunk_ids"]))
        for ref in cases[r["id"]]["references"] if ref["role"]=="candidate_support") for r in retrieval)
    summary["bm25_at_8_equal_budget"] = {"hit_references":bm8,"candidate_references":total_refs,"micro":bm8/total_refs}
    probe = next((r for r in rows if r['test']=='A_probe'),None)
    if probe is None:
        settings, store, docs, chunks, readers=corpus()
        scope=[c for c in chunks if c.document_id==docs['lightrag'].id]
        query='What do low-level retrieval and high-level retrieval focus on in LightRAG?'
        hits=retrieve(query,scope,10)
        targets=cases['A08']['references']
        scores={str(k):sum(bool({h.chunk.id for h in hits[:k]}.intersection(r['equivalent_chunk_ids'])) for r in targets)/len(targets) for k in (5,10)}
        alternatives=[]
        # Post-hoc alternative locations reveal incompleteness of candidate gold;
        # preserve original scores, do not retrofit a better-looking test set.
        for suffix in ('p0004_c0004','p0004_c0005'):
            chunk=next(c for c in scope if c.id.endswith(suffix))
            text=norm(chunk.text)
            marker='Low-Level Retrieval.' if 'c0004' in suffix else 'High-Level Retrieval.'
            start=text.index(marker)
            quote=text[start:start+220]
            assert quote in norm(readers['lightrag'].pages[3].extract_text() or '')
            alternatives.append({'chunk_id':chunk.id,'paper_id':'lightrag','page':4,'quote':quote,'label':'provisional_posthoc_not_in_primary_metrics'})
        probe=record('A_probe','matched_phrasing',scope='lightrag only; same two candidate references as A08/A09',
            explicit_terms_question=query,explicit_terms_recall=scores,ordered_chunk_ids=[h.chunk.id for h in hits],
            chinese_source_case='A08',synonym_source_case='A09',posthoc_alternative_references=alternatives,formal_metric=False)
    summary['matched_phrasing_probe']=probe
    analyses_done = {(r["id"],r.get("repair")) for r in rows if r["test"]=="C_analysis" and r.get("analysis_revision")==2}
    for row in (r for r in rows if r["test"] == "C"):
        result = row["raw_result"]
        initial, later, repairing = set(), set(), False
        initial_states = {}
        repair_queries, triggered = [], []
        for event in result["trace"]:
            if not repairing:
                initial_states.update(event["metadata"].get("requirement_statuses",{}))
            if event["type"] == "repair_start":
                repairing = True; repair_queries=event["metadata"].get("queries",[]);triggered=event["node_ids"]
            if event["type"] in {"retrieve","graph_expand","repair_retrieve"}:
                (later if repairing else initial).update(event["node_ids"])
        new = later-initial
        accepted = {e["chunk_id"] for e in result["evidence"] if e["validated"] and e["round"] == 1}
        refs=[r for r in cases[row["id"]]["references"] if r["role"]=="candidate_support"]
        reference_retrieval = {stage: (sum(bool(ids.intersection(r["equivalent_chunk_ids"])) for r in refs)/len(refs)) if refs else None
            for stage, ids in (("initial",initial),("union_after_repair",initial|later))}
        new_refs = [r["reference_id"] for r in refs if new.intersection(r["equivalent_chunk_ids"])]
        entry={"case_id":row["id"],"repair":row["repair"],"run_id":result["run_id"],
            "supported":result["stats"]["supported_requirements"],"requirements":result["stats"]["total_requirements"],
            "unresolved":result["stats"]["total_requirements"]-result["stats"]["supported_requirements"],
            "duration_ms":result["stats"]["duration_ms"],"actual_requests":row["actual_requests"],"tokens":row["total_tokens"],
            "repair_rounds":result["stats"]["repair_rounds"],"stop":result["stats"]["stop_reason"],
            "initial_evidence_ids":sorted(initial),"repair_evidence_ids":sorted(later),"new_retrieved_chunk_ids":sorted(new),
            "new_model_accepted_chunk_ids":sorted(accepted & new),"reused_model_accepted_chunk_ids":sorted(accepted & initial),
            "triggered_requirement_ids":triggered,"repair_queries":repair_queries,
            "candidate_reference_retrieval_coverage":reference_retrieval,"new_candidate_reference_ids":new_refs,
            "semantic_reference_coverage":None,"semantic_reason":"provisional, model acceptance is not semantic gold",
            "initial_model_supported":sum(s=="supported" for s in initial_states.values()),
            "within_run_model_support_delta":result["stats"]["supported_requirements"]-sum(s=="supported" for s in initial_states.values()),
            "derivation_version":"trace_stages_v2","supersedes_raw_C_derived_fields":True}
        entry["analysis_revision"] = 2
        summary["online"].append(entry)
        if (row["id"],row["repair"]) not in analyses_done:
            record("C_analysis",row["id"],**{k:v for k,v in entry.items() if k!="case_id"})
    summary["online_actual_requests"] = sum(r["actual_requests"] for r in summary["online"])
    summary["online_reported_tokens"] = sum(r["tokens"] or 0 for r in summary["online"])
    summary["online_model_returned"] = sorted({c.get("model_returned","") for r in rows if r["test"]=="C" for c in r["sdk_calls"]})
    summary["pairing"] = []
    for ident in ("A04","A08","A10"):
        paired=[r for r in rows if r["test"]=="C" and r["id"]==ident]
        if len(paired)==2:
            plans=[[o["result"] for o in r["observations"] if o["type"]=="plan"] for r in paired]
            initial=[next(a["initial_evidence_ids"] for a in summary["online"] if a["case_id"]==ident and a["repair"]==r["repair"]) for r in paired]
            summary["pairing"].append({"case_id":ident,"plans_identical":plans[0]==plans[1],"initial_evidence_identical":initial[0]==initial[1],"strict_pair":False})
    summary["boundary"] = next((r for r in rows if r["test"]=="A_boundary"),None)
    summary["derivation_note"] = "Initial C instrumentation mistook the first audit for the initial evidence when retrieval was empty. Original C rows retained; use C_analysis trace_stages_v2 derived from retrieve/graph_expand before repair_start. No online reruns or output relabeling."
    save(OUT / "d6_metrics.json",summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in {"online","boundary","derivation_note"}},ensure_ascii=False))
    for r in summary["online"]:
        print(json.dumps(r,ensure_ascii=False))


if __name__=="__main__":
    main()
