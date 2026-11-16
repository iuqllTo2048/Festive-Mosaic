"""Literal term provenance and bounded shared-term expansion, not semantic KG extraction."""
import hashlib
import re
from dataclasses import dataclass

from .retrieve import RetrievalHit
from .schemas import Chunk, Document, EvidenceLink, GraphData, GraphEdge, GraphNode, Provenance, Requirement

TERM_PATTERN = re.compile(r"\b(?:[A-Z][a-zA-Z]*[A-Z0-9][a-zA-Z0-9]*|[A-Z][a-z]+(?:-[A-Z][a-zA-Z0-9]+)+)\b")
COMMON_TERMS = {"rag", "llm", "llms", "ai", "pdf", "nlp", "url", "api", "http", "https"}


@dataclass(frozen=True)
class TermMention:
    chunk_id: str
    name: str
    normalized_name: str
    char_start: int
    char_end: int


def extract_mentions(chunks: list[Chunk]) -> list[TermMention]:
    mentions = []
    for chunk in chunks:
        seen = set()
        for match in TERM_PATTERN.finditer(chunk.text):
            term = match.group().casefold()
            if term in seen or term in COMMON_TERMS or len(term) < 3:
                continue
            seen.add(term)
            mentions.append(TermMention(chunk.id, match.group(), term, match.start(), match.end()))
            if len(seen) == 3:
                break
    return mentions


def expand_shared_terms(seeds: list[RetrievalHit], chunks: list[Chunk], mentions: list[TermMention],
                        limit: int = 2) -> tuple[list[RetrievalHit], dict[str, list[str]]]:
    by_chunk: dict[str, set[str]] = {}
    for mention in mentions:
        by_chunk.setdefault(mention.chunk_id, set()).add(mention.normalized_name)
    seed_ids = {hit.chunk.id for hit in seeds}
    seed_terms = set().union(*(by_chunk.get(chunk_id, set()) for chunk_id in seed_ids))
    shared = {chunk.id: sorted(seed_terms & by_chunk.get(chunk.id, set())) for chunk in chunks
              if chunk.id not in seed_ids}
    candidates = sorted((chunk for chunk in chunks if shared.get(chunk.id)),
                        key=lambda chunk: (-len(shared[chunk.id]), chunk.id))
    additions = candidates[:max(0, min(limit, 8 - len(seeds)))]
    return [*seeds, *(RetrievalHit(chunk, 0) for chunk in additions)], {chunk.id: shared[chunk.id] for chunk in additions}


def relation_id(kind: str, source: str, target: str) -> str:
    return "edge_" + hashlib.sha256(f"{kind}:{source}:{target}".encode()).hexdigest()[:24]


def build_graph(chunks: list[Chunk], documents: dict[str, Document], requirements: list[Requirement],
                evidence: list[EvidenceLink], mentions: list[TermMention], enabled: bool) -> GraphData:
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}

    def connect(source, target, kind, provenance):
        edge_id = relation_id(kind, source, target)
        edges[edge_id] = GraphEdge(id=edge_id, source=source, target=target, type=kind, provenance=provenance)

    for requirement in requirements:
        nodes[requirement.id] = GraphNode(id=requirement.id, type="requirement", label=requirement.text, status=requirement.status)
    for chunk in chunks:
        document = documents[chunk.document_id]
        nodes[document.id] = GraphNode(id=document.id, type="paper", label=document.title,
                                      source_ref=Provenance(method="pdf_ingestion", document_id=document.id))
        source = Provenance(method="pdf_ingestion", document_id=document.id, chunk_id=chunk.id, page=chunk.page_number)
        nodes[chunk.id] = GraphNode(id=chunk.id, type="chunk", label=f"第 {chunk.page_number} 页 · 片段 {chunk.order + 1}", source_ref=source)
        connect(document.id, chunk.id, "contains", source)
    if enabled:
        counts: dict[str, int] = {}
        for mention in mentions:
            if mention.chunk_id not in nodes or counts.get(mention.chunk_id, 0) >= 3:
                continue
            counts[mention.chunk_id] = counts.get(mention.chunk_id, 0) + 1
            chunk = next(chunk for chunk in chunks if chunk.id == mention.chunk_id)
            concept_id = "concept_" + hashlib.sha256(mention.normalized_name.encode()).hexdigest()[:16]
            provenance = Provenance(method="literal_terms_v1", document_id=chunk.document_id, chunk_id=chunk.id,
                                    page=chunk.page_number, char_start=mention.char_start,
                                    char_end=mention.char_end, term=mention.name)
            nodes.setdefault(concept_id, GraphNode(id=concept_id, type="concept", label=mention.name, source_ref=provenance))
            connect(chunk.id, concept_id, "mentions", provenance)
    accepted_ids = {item for requirement in requirements if requirement.status == "supported" for item in requirement.evidence_ids}
    for link in evidence:
        if link.validated and link.id in accepted_ids and link.chunk_id in nodes:
            connect(link.chunk_id, link.requirement_id, "supports", Provenance(
                method="quote_checked_model_support", chunk_id=link.chunk_id,
                document_id=link.document_id, page=link.page, evidence_id=link.id,
            ))
    return GraphData(nodes=list(nodes.values()), edges=list(edges.values()), concept_expansion_enabled=enabled,
                     note="仅为原文术语共现扩展，非语义知识图谱。" if enabled else "本次未启用概念扩展，仅显示真实证据来源关系。")
