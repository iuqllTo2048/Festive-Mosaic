import re
import time
from uuid import uuid4

from .config import Settings
from .errors import IngestError
from .llm import DeepSeekClient
from .retrieve import retrieve
from .schemas import AnswerParagraph, Citation, QueryRequest, QueryResult, QueryStats
from .store import Store


def normalize_quote(text: str) -> str:
    return " ".join(text.split())


def run_query(body: QueryRequest, store: Store, settings: Settings, llm: DeepSeekClient) -> QueryResult:
    started = time.monotonic()
    question = body.question.strip()
    if not question:
        raise IngestError("empty_question", "请输入研究问题。", 400)
    if not settings.deepseek_api_key.get_secret_value().strip():
        raise IngestError("llm_not_configured", "尚未配置 DEEPSEEK_API_KEY，请在后端环境变量中设置。", 503)
    documents = {document.id: document for document in store.list_documents()}
    if body.document_ids and any(document_id not in documents for document_id in body.document_ids):
        raise IngestError("document_not_found", "选定的文档不存在，请刷新语料列表。", 404)
    if not documents:
        raise IngestError("empty_library", "请先上传或导入至少一篇文本型 PDF。", 400)
    hits = retrieve(question, store.retrieval_chunks(body.document_ids), body.top_k)
    paragraphs: list[AnswerParagraph] = []
    citations: list[Citation] = []
    insufficient: list[str] = []
    requests = 0
    if not hits:
        insufficient.append("当前语料未检索到匹配片段，无法确定。BM25 依赖词面匹配，英文论文建议在问题中保留英文术语。")
    else:
        proposed, requests = llm.answer(question, hits)
        insufficient.extend(proposed.insufficient)
        lookup = {hit.chunk.id: hit.chunk for hit in hits}
        citation_lookup: dict[tuple[str, str], str] = {}
        for paragraph in proposed.paragraphs:
            valid = bool(paragraph.text.strip()) and not re.search(r"\[\s*\d+\s*\]", paragraph.text)
            for candidate in paragraph.citations:
                chunk = lookup.get(candidate.chunk_id)
                quote = normalize_quote(candidate.quote)
                if chunk is None or not quote or quote not in normalize_quote(chunk.text):
                    valid = False
            if not valid:
                insufficient.append("一段候选回答的引文无法在本轮检索原文中核对，已移除该段。")
                continue
            ids = []
            for candidate in paragraph.citations:
                chunk = lookup[candidate.chunk_id]
                quote = normalize_quote(candidate.quote)
                signature = (chunk.id, quote)
                if signature not in citation_lookup:
                    citation_id = str(len(citations) + 1)
                    citation_lookup[signature] = citation_id
                    document = documents[chunk.document_id]
                    citations.append(Citation(
                        id=citation_id, document_id=document.id, document_title=document.title,
                        chunk_id=chunk.id, page=chunk.page_number, quote=quote,
                        pdf_url=f"{document.pdf_url}#page={chunk.page_number}",
                    ))
                ids.append(citation_lookup[signature])
            paragraphs.append(AnswerParagraph(text=paragraph.text.strip(), citation_ids=list(dict.fromkeys(ids))))
    if not paragraphs:
        insufficient.append("当前语料无法确定：没有生成带有效原文引用的回答。")
    answer = "\n\n".join(paragraph.text + " " + "".join(f"[{ref}]" for ref in paragraph.citation_ids) for paragraph in paragraphs)
    result = QueryResult(
        run_id=str(uuid4()), question=question, answer=answer or "当前语料无法确定。",
        paragraphs=paragraphs, citations=citations, insufficient=list(dict.fromkeys(insufficient)),
        status="answered" if paragraphs else "insufficient", model=settings.deepseek_model if requests else None,
        stats=QueryStats(retrieved_chunks=len(hits), llm_requests=requests,
                         duration_ms=round((time.monotonic() - started) * 1000)),
    )
    store.save_run(result)
    return result
