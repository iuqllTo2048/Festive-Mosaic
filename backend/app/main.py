import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from .config import Settings
from .errors import IngestError
from .ingest import ingest_pdf
from .schemas import ChunkPage, Document, ErrorResponse, Health, IngestResult, SeedPaper, SeedRequest, SeedResult
from .seed import import_paper, load_papers
from .store import Store
from .llm import DeepSeekClient
from .query import run_query
from .schemas import QueryRequest, QueryResult, Chunk

logger = logging.getLogger("verifiatlas")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    store = Store(settings.resolved_data_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.initialize()
        yield

    app = FastAPI(title="VerifiAtlas——面向科研知识探索的智能交互可视化系统", version="0.1.0", lifespan=lifespan,
                  responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse},
                             413: {"model": ErrorResponse}, 415: {"model": ErrorResponse},
                             422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
    app.state.store = store
    app.state.llm = DeepSeekClient(settings)

    @app.exception_handler(IngestError)
    async def ingest_error(request: Request, exc: IngestError):
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": {
            "code": "invalid_request", "message": "请求参数不正确，请检查文件、页码或论文编号。"
        }})

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        # No request body, PDF contents, user path, or environment secrets in the log.
        logger.error("Request failed: %s %s", request.method, type(exc).__name__)
        return JSONResponse(status_code=500, content={"error": {
            "code": "internal_error", "message": "本地服务处理失败，请检查数据目录可写性与服务日志。"
        }})

    def require_document(document_id: str) -> Document:
        document = store.get_document(document_id)
        if document is None:
            raise IngestError("document_not_found", "文档不存在。", 404)
        return document

    @app.get("/api/health", response_model=Health)
    def health():
        with store.connect() as db:
            db.execute("SELECT 1").fetchone()
        return Health(max_upload_mb=settings.max_upload_mb, max_pdf_pages=settings.max_pdf_pages,
                      llm_configured=bool(settings.deepseek_api_key.get_secret_value().strip()),
                      llm_model=settings.deepseek_model)

    @app.post("/api/query", response_model=QueryResult)
    def query(body: QueryRequest):
        return run_query(body, store, settings, app.state.llm)

    @app.get("/api/runs/{run_id}", response_model=QueryResult)
    def saved_run(run_id: str):
        result = store.get_run(run_id)
        if result is None:
            raise IngestError("run_not_found", "问答记录不存在。", 404)
        return result

    @app.get("/api/chunks/{chunk_id}", response_model=Chunk)
    def source_chunk(chunk_id: str):
        chunk = store.get_chunk(chunk_id)
        if chunk is None:
            raise IngestError("chunk_not_found", "来源片段不存在。", 404)
        return chunk

    @app.get("/api/documents", response_model=list[Document])
    def documents():
        return store.list_documents()

    @app.post("/api/documents/upload", response_model=IngestResult)
    def upload(file: Annotated[UploadFile, File()]):
        try:
            content = file.file.read(settings.max_upload_bytes + 1)
            return ingest_pdf(content, file.filename or "", store, settings)
        finally:
            file.file.close()

    @app.get("/api/documents/{document_id}/chunks", response_model=ChunkPage)
    def chunks(document_id: str, page: Annotated[int | None, Query(ge=1)] = None,
               offset: Annotated[int, Query(ge=0)] = 0,
               limit: Annotated[int, Query(ge=1, le=100)] = 30):
        document = require_document(document_id)
        if page is not None and page > document.page_count:
            raise IngestError("page_not_found", "页码超过文档实际页数。", 404)
        return store.list_chunks(document_id, page, offset, limit)

    @app.get("/api/documents/{document_id}/pdf", response_class=FileResponse)
    def pdf(document_id: str):
        document = require_document(document_id)
        path = store.pdf_path(document)
        if not path.is_file():
            raise IngestError("pdf_not_found", "原 PDF 文件缺失，请检查本地数据目录。", 404)
        return FileResponse(path, media_type="application/pdf", filename=document.original_filename,
                            content_disposition_type="inline", headers={"X-Content-Type-Options": "nosniff"})

    @app.get("/api/papers", response_model=list[SeedPaper])
    def papers():
        return load_papers()

    @app.post("/api/documents/seed", response_model=list[SeedResult])
    def seed(body: SeedRequest):
        manifest = {paper.id: paper for paper in load_papers()}
        if any(paper_id not in manifest for paper_id in body.paper_ids):
            raise IngestError("unknown_paper", "论文编号不存在，请从官方来源清单中选择。", 400)
        return [import_paper(manifest[paper_id], store, settings) for paper_id in dict.fromkeys(body.paper_ids)]

    return app


app = create_app()
