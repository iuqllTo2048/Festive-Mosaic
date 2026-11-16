from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ApiError


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    stage: Literal["D3"] = "D3"
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
    mode: Literal["basic", "audited"] = "basic"
    enable_repair: bool = True
    enable_graph_expansion: bool = True


class Citation(BaseModel):
    id: str
    document_id: str
    document_title: str
    chunk_id: str
    page: int
    quote: str
    pdf_url: str
    evidence_id: str | None = None


class AnswerParagraph(BaseModel):
    text: str
    citation_ids: list[str]


class Requirement(BaseModel):
    id: str
    text: str
    search_query: str
    status: Literal["pending", "supported", "insufficient"] = "pending"
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str = ""


class EvidenceLink(BaseModel):
    id: str
    requirement_id: str
    chunk_id: str
    quote: str
    validated: bool
    verifier_result: str
    reason: str
    round: int
    document_id: str | None = None
    page: int | None = None


class Provenance(BaseModel):
    method: str
    document_id: str | None = None
    chunk_id: str | None = None
    page: int | None = None
    evidence_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    term: str | None = None


class GraphNode(BaseModel):
    id: str
    type: Literal["paper", "chunk", "concept", "requirement"]
    label: str
    status: Literal["pending", "supported", "insufficient"] | None = None
    source_ref: Provenance | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: Literal["contains", "mentions", "supports"]
    provenance: Provenance


class GraphData(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    concept_expansion_enabled: bool = False
    note: str = "基础问答未构建图数据。"


class TraceEvent(BaseModel):
    step: int
    type: str
    timestamp: str
    description: str
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | list[str] | dict[str, str]] = Field(default_factory=dict)


class QueryStats(BaseModel):
    retrieved_chunks: int
    llm_requests: int
    duration_ms: int
    total_requirements: int = 0
    supported_requirements: int = 0
    repair_rounds: int = 0
    display_coverage_ratio: float = 0
    graph_expanded_chunks: int = 0
    stop_reason: str = "basic_completed"


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
    mode: Literal["basic", "audited"] = "basic"
    requirements: list[Requirement] = Field(default_factory=list)
    audit_version: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)
    graph: GraphData = Field(default_factory=GraphData)
    trace: list[TraceEvent] = Field(default_factory=list)


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


class PlannedRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=300)
    search_query: str = Field(min_length=1, max_length=600)


class RequirementPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements: list[PlannedRequirement] = Field(min_length=1, max_length=4)


class RequirementJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    requirement_id: str = Field(min_length=1, max_length=100)
    status: Literal["supported", "insufficient"]
    explanation: str = Field(min_length=1, max_length=500)
    answer: str = Field(default="", max_length=1000)
    evidence: list[ProposedCitation] = Field(default_factory=list, max_length=3)
    repair_query: str | None = Field(default=None, max_length=600)


class AuditProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judgments: list[RequirementJudgment] = Field(min_length=1, max_length=4)
