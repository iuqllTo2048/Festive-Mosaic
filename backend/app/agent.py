"""Finite evidence audit: plan -> retrieve/expand -> verify -> at most one repair -> stop."""
import re
import time
import unicodedata
from datetime import datetime, timezone
from uuid import uuid4

from .config import Settings
from .errors import IngestError
from .graph import build_graph, expand_shared_terms, extract_mentions, relation_id
from .llm import DeepSeekClient, RunBudget
from .query import normalize_quote
from .retrieve import retrieve, RetrievalHit
from .schemas import (AnswerParagraph, Citation, EvidenceLink, QueryRequest, QueryResult, QueryStats,
                      Requirement, TraceEvent)
from .store import Store

FACT_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*|\d+(?:\.\d+)?")
DEFINITION_TASK = re.compile(r"全称|缩写|术语定义|概念定义|英文(?:论文)?表述|full\s+name|acronym|stands?\s+for|defin(?:e|ed|ition)", re.I)


def literal_claim_tokens_match(text: str, sources: list[str]) -> bool:
    """Conservative term/number check, not a semantic entailment proof."""
    source = unicodedata.normalize("NFKC", "\n".join(sources))
    source = re.sub(r"(?<=[A-Za-z])-\s*\n\s*(?=[a-z])", "", source)
    source = re.sub(r"-\s+", "-", source)
    available = {token.casefold() for token in FACT_TOKEN.findall(source)}
    proposed = FACT_TOKEN.findall(unicodedata.normalize("NFKC", text))
    return all(token.casefold() in available for token in proposed)


def run_audited_query(body: QueryRequest, store: Store, settings: Settings, llm: DeepSeekClient) -> QueryResult:
    started = time.monotonic()
    run_id = str(uuid4())
    budget = RunBudget(settings)
    documents = {document.id: document for document in store.list_documents()}
    corpus = store.retrieval_chunks(body.document_ids)
    requirements: list[Requirement] = []
    evidence: list[EvidenceLink] = []
    trace: list[TraceEvent] = []
    seen_chunks = {}
    answers: dict[str, str] = {}
    repair_queries: dict[str, str] = {}
    expanded_ids = set()
    repair_rounds = 0
    stop_reason = "completed"
    concepts_enabled = False
    mentions = []

    def event(kind, description, node_ids=None, edge_ids=None, **metadata):
        trace.append(TraceEvent(step=len(trace) + 1, type=kind, timestamp=datetime.now(timezone.utc).isoformat(),
                                description=description, node_ids=node_ids or [], edge_ids=edge_ids or [], metadata=metadata))

    def context_for(seeds):
        nonlocal mentions
        for hit in seeds:
            seen_chunks[hit.chunk.id] = hit.chunk
        if concepts_enabled:
            hits, additions = expand_shared_terms(seeds, corpus, mentions, 2)
            expanded_ids.update(additions)
            for hit in hits:
                seen_chunks[hit.chunk.id] = hit.chunk
            event("graph_expand", f"通过共享原文术语扩展 {len(additions)} 个片段，最多2个。",
                  node_ids=[hit.chunk.id for hit in hits], added_chunk_ids=list(additions),
                  shared_terms={key: ", ".join(value) for key, value in additions.items()})
            return hits
        return seeds

    def verify(pending, hits, round_number):
        if not hits:
            for requirement in pending:
                requirement.status = "insufficient"
                requirement.explanation = "本轮未检索到可用片段。"
            event("verify", "无可用片段，需求保守标为证据不足；未调用模型验证。",
                  node_ids=[item.id for item in pending], round=round_number,
                  requirement_statuses={item.id: item.status for item in requirements})
            return
        proposal = llm.audit(body.question, pending, hits, budget)
        expected = {item.id for item in pending}
        received = [item.requirement_id for item in proposal.judgments]
        if set(received) != expected or len(received) != len(expected):
            raise IngestError("invalid_audit_ids", "模型审计的需求编号不完整或重复，本轮不能判定支持。", 502)
        lookup = {hit.chunk.id: hit.chunk for hit in hits}
        by_id = {item.requirement_id: item for item in proposal.judgments}
        for requirement in pending:
            judgment = by_id[requirement.id]
            repair_queries[requirement.id] = (judgment.repair_query or requirement.search_query).strip() or requirement.search_query
            accepted = []
            candidates = []
            for candidate in judgment.evidence:
                chunk = lookup.get(candidate.chunk_id)
                quote = normalize_quote(candidate.quote)
                quote_matches = chunk is not None and bool(quote) and quote in normalize_quote(chunk.text)
                valid = judgment.status == "supported" and quote_matches
                link = EvidenceLink(
                    id=f"ev_{run_id}_{len(evidence) + 1}", requirement_id=requirement.id,
                    chunk_id=candidate.chunk_id, quote=quote, validated=valid,
                    verifier_result=judgment.status,
                    reason="模型提出支持且原文引句匹配" if valid else "引文无法定位或模型未判为支持",
                    round=round_number, document_id=chunk.document_id if chunk else None,
                    page=chunk.page_number if chunk else None,
                )
                evidence.append(link)
                candidates.append(link)
                if valid:
                    accepted.append(link.id)
            valid_answer = bool(judgment.answer.strip()) and not re.search(r"\[\s*\d+\s*\]", judgment.answer)
            claim_matches = literal_claim_tokens_match(
                judgment.answer + "\n" + judgment.explanation,
                [lookup[link.chunk_id].text for link in candidates if link.chunk_id in lookup],
            )
            valid_answer = valid_answer and claim_matches
            supported = judgment.status == "supported" and bool(accepted) and len(accepted) == len(candidates) and valid_answer
            requirement.status = "supported" if supported else "insufficient"
            requirement.evidence_ids = accepted if supported else []
            requirement.explanation = judgment.explanation if supported or judgment.status == "insufficient" else (
                "模型提出支持，但回答中的术语或数值未在所引用片段中出现。" if not claim_matches else "模型提出支持，但引句或回答未通过后端校验。")
            if supported:
                answers[requirement.id] = judgment.answer.strip()
            else:
                for link in candidates:
                    link.validated = False
                    if judgment.status == "supported":
                        link.reason = "该需求未通过完整校验：回答无效、缺少证据或包含无法核对的引句。"
            event("verify_requirement", f"{requirement.text}：{'有引用支持' if supported else '证据不足'}。",
                  node_ids=[requirement.id, *(lookup[link.chunk_id].id for link in candidates if link.chunk_id in lookup)],
                  edge_ids=[relation_id("supports", link.chunk_id, requirement.id) for link in candidates if link.validated],
                  round=round_number, requirement_statuses={item.id: item.status for item in requirements})

    event("run_start", "开始本轮本地证据审计。", document_ids=body.document_ids or list(documents),
          repair_enabled=body.enable_repair, graph_expansion_requested=body.enable_graph_expansion,
          top_k=body.top_k, max_requests=settings.agent_max_requests,
          timeout_seconds=settings.agent_timeout_seconds)
    try:
        plan = llm.plan(body.question, budget)
        planned = [item for item in plan.requirements
                   if not DEFINITION_TASK.search(item.text) or DEFINITION_TASK.search(body.question)]
        pruned = len(plan.requirements) - len(planned)
        if not planned:
            planned = [plan.requirements[0].model_copy(update={"text": body.question[:300], "search_query": body.question[:600]})]
        requirements = [Requirement(id=f"req_{run_id}_{index + 1}", text=item.text, search_query=item.search_query)
                        for index, item in enumerate(planned)]
        event("plan", f"拆解为 {len(requirements)} 个可核验需求。", node_ids=[item.id for item in requirements],
              pruned_unrequested_definitions=pruned,
              requirement_statuses={item.id: item.status for item in requirements})
        if body.enable_graph_expansion:
            try:
                mentions = extract_mentions(corpus)
                store.save_concept_mentions(mentions)
                concepts_enabled = bool(mentions)
                event("concept_index", "已记录原文术语与字符位置。" if concepts_enabled else "未提取到可用术语，本次退化为来源关系图。",
                      enabled=concepts_enabled, mentions=len(mentions))
            except Exception:
                event("concept_index", "术语索引失败，本次未启用概念扩展。", enabled=False)
        else:
            event("concept_index", "本次按请求关闭概念扩展。", enabled=False)
        budget.check()
        seeds = retrieve(body.question, corpus, min(body.top_k, 6))
        event("retrieve", f"初次 BM25 检索返回 {len(seeds)} 个种子片段。", node_ids=[hit.chunk.id for hit in seeds],
              query=body.question, round=0)
        hits = context_for(seeds)
        verify(requirements, hits, 0)
        gaps = [item for item in requirements if item.status != "supported"]
        if gaps and body.enable_repair:
            budget.check()
            repair_rounds = 1
            queries = [repair_queries.get(item.id, item.search_query) for item in gaps]
            event("repair_start", f"针对 {len(gaps)} 个缺口执行唯一一轮定向补检。",
                  node_ids=[item.id for item in gaps], queries=queries, round=1)
            pools = [retrieve(query, corpus, min(body.top_k, 6)) for query in queries]
            repair_seeds: list[RetrievalHit] = []
            selected = set()
            for index in range(max((len(pool) for pool in pools), default=0)):
                for pool in pools:
                    if index < len(pool) and pool[index].chunk.id not in selected and len(repair_seeds) < 6:
                        selected.add(pool[index].chunk.id)
                        repair_seeds.append(pool[index])
            event("repair_retrieve", f"补检返回 {len(repair_seeds)} 个去重种子片段。",
                  node_ids=[hit.chunk.id for hit in repair_seeds], round=1)
            verify(gaps, context_for(repair_seeds), 1)
            stop_reason = "repair_exhausted" if any(item.status != "supported" for item in requirements) else "covered_after_repair"
        elif gaps:
            stop_reason = "repair_disabled"
        else:
            stop_reason = "all_supported"
    except IngestError as exc:
        stop_reason = exc.code
        if not requirements:
            requirements = [Requirement(id=f"req_{run_id}_1", text=body.question[:300], search_query=body.question[:600],
                                        status="insufficient", explanation="需求规划未完成：" + exc.message)]
        for requirement in requirements:
            if requirement.status != "supported":
                requirement.status = "insufficient"
                requirement.explanation = "审计未完成：" + exc.message
        event("error", exc.message, code=exc.code, llm_requests=budget.requests)

    citations: list[Citation] = []
    paragraphs: list[AnswerParagraph] = []
    accepted = {item.id: item for item in evidence if item.validated}
    for requirement in requirements:
        ids = []
        for evidence_id in requirement.evidence_ids:
            link = accepted[evidence_id]
            document = documents[link.document_id]
            citation_id = str(len(citations) + 1)
            citations.append(Citation(id=citation_id, document_id=document.id, document_title=document.title,
                                      chunk_id=link.chunk_id, page=link.page, quote=link.quote,
                                      pdf_url=f"{document.pdf_url}#page={link.page}", evidence_id=link.id))
            ids.append(citation_id)
        if ids:
            paragraphs.append(AnswerParagraph(text=answers[requirement.id], citation_ids=ids))
    for requirement in requirements:
        if requirement.status == "pending":
            requirement.status = "insufficient"
            requirement.explanation = "审计未完成，不能判为支持。"
    graph = build_graph(list(seen_chunks.values()), documents, requirements, evidence, mentions, concepts_enabled)
    supported = sum(item.status == "supported" for item in requirements)
    insufficient = [f"{item.text}：{item.explanation}" for item in requirements if item.status != "supported"]
    if not concepts_enabled:
        insufficient.append("本次未启用概念扩展，仅构建论文、片段和需求的来源关系。")
    event("stop", "本轮已停止；不会继续补检。", node_ids=[item.id for item in requirements],
          reason=stop_reason, repair_rounds=repair_rounds, supported=supported,
          requirement_statuses={item.id: item.status for item in requirements})
    answer = "\n\n".join(item.text + " " + "".join(f"[{ref}]" for ref in item.citation_ids) for item in paragraphs)
    result = QueryResult(
        run_id=run_id, question=body.question, answer=answer or "当前语料无法确定。", paragraphs=paragraphs,
        citations=citations, insufficient=insufficient, status="answered" if paragraphs else "insufficient",
        model=settings.deepseek_model if budget.requests else None, mode="audited", requirements=requirements,
        audit_version="literal_claims_v1",
        evidence=evidence, graph=graph, trace=trace,
        stats=QueryStats(retrieved_chunks=len(seen_chunks), llm_requests=budget.requests,
                         duration_ms=round((time.monotonic() - started) * 1000), total_requirements=len(requirements),
                         supported_requirements=supported, repair_rounds=repair_rounds,
                         display_coverage_ratio=supported / len(requirements), graph_expanded_chunks=len(expanded_ids),
                         stop_reason=stop_reason),
    )
    store.save_run(result)
    return result
