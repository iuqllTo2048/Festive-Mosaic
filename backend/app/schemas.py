from typing import Literal

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ApiError


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    stage: Literal["D1"] = "D1"
    max_upload_mb: int
    max_pdf_pages: int


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
