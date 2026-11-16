from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ApiError


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    stage: Literal["D2"] = "D2"
    max_upload_mb: int
    max_pdf_pages: int
    llm_configured: bool
    llm_model: str


class Document(BaseModel):
    id: str
    title: str
    original_filename: str
    authors: list[str]
    year: int | None
    source_url: str | None
    source_pdf_url: str | None
    retrieved_at: str | None
    sha256: str
    page_count: int
    chunk_count: int
    ingest_status: Literal["ready", "ready_with_warnings"]
    warnings: list[str]
    created_at: str
    pdf_url: str


class Chunk(BaseModel):
    id: str
    document_id: str
    page_number: int
    text: str
    order: int
    char_start: int
    char_end: int


class ChunkPage(BaseModel):
    items: list[Chunk]
    total: int
    offset: int
    limit: int


class IngestResult(BaseModel):
    document: Document
    duplicate: bool


class SeedPaper(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int
    source_url: str
    pdf_url: str
    import_note: str


class SeedRequest(BaseModel):
    paper_ids: list[str] = Field(min_length=1, max_length=3)


class SeedResult(BaseModel):
    paper_id: str
    status: Literal["imported", "duplicate", "failed"]
    document: Document | None = None
    error: ApiError | None = None
    manual_url: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] | None = Field(default=None, min_length=1, max_length=20)
    top_k: int = Field(default=6, ge=1, le=8)


class Citation(BaseModel):
    id: str
    document_id: str
    document_title: str
    chunk_id: str
    page: int
    quote: str
    pdf_url: str


class AnswerParagraph(BaseModel):
    text: str
    citation_ids: list[str]


class QueryStats(BaseModel):
    retrieved_chunks: int
    llm_requests: int
    duration_ms: int


class QueryResult(BaseModel):
    run_id: str
    question: str
    answer: str
    paragraphs: list[AnswerParagraph]
    citations: list[Citation]
    insufficient: list[str]
    status: Literal["answered", "insufficient"]
    model: str | None
    stats: QueryStats


class ProposedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str = Field(min_length=1, max_length=160)
    quote: str = Field(min_length=12, max_length=300)


class ProposedParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1200)
    citations: list[ProposedCitation] = Field(min_length=1, max_length=4)


class ProposedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paragraphs: list[ProposedParagraph] = Field(max_length=6)
    insufficient: list[str] = Field(max_length=8)
