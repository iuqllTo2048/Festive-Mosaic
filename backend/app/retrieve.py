"""Small-corpus lexical BM25 retrieval; no embeddings, rewriting, or graph expansion."""
import re
import unicodedata
from dataclasses import dataclass

from rank_bm25 import BM25Plus

from .schemas import Chunk

STOP_WORDS = set("a an the of and or to in is are was were be been on for with as by from what which how does do did can this that it its at into have has".split())


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "", text)
    return [term for term in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text)
            if term not in STOP_WORDS]


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float


def retrieve(question: str, chunks: list[Chunk], top_k: int = 6) -> list[RetrievalHit]:
    query = tokenize(question)
    if not query or not chunks:
        return []
    corpus = [tokenize(chunk.text) for chunk in chunks]
    if not any(corpus):
        return []
    scores = BM25Plus(corpus).get_scores(query)
    query_terms = set(query)
    ranked = sorted(
        (RetrievalHit(chunk, float(score)) for chunk, tokens, score in zip(chunks, corpus, scores)
         if query_terms.intersection(tokens)),
        key=lambda hit: (-hit.score, hit.chunk.id),
    )
    return ranked[:top_k]
