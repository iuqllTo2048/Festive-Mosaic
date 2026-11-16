import hashlib
import io
import threading
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from .config import Settings
from .errors import IngestError
from .schemas import Chunk, Document, IngestResult, SeedPaper
from .store import Store

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
# Serializes file+SQLite ingestion in this local, single-process application.
INGEST_LOCK = threading.Lock()


def parse_pdf(content: bytes, document_id: str, max_pages: int) -> tuple[list[Chunk], int, list[str], str]:
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise IngestError("encrypted_pdf", "暂不支持加密 PDF，请先解密后上传。")
        page_count = len(reader.pages)
        if not page_count:
            raise IngestError("empty_pdf", "PDF 没有页面。")
        if page_count > max_pages:
            raise IngestError("too_many_pages", f"PDF 共 {page_count} 页，最多支持 {max_pages} 页。")
        title = str((reader.metadata or {}).get("/Title", "")).strip()
        chunks: list[Chunk] = []
        warnings: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = (page.extract_text() or "").strip()
            except Exception as exc:
                raise IngestError("page_parse_failed", f"第 {number} 页解析失败，未导入该文件。") from exc
            if not text:
                warnings.append(f"第 {number} 页未提取到文本：可能为空白或扫描图片；暂不支持 OCR。")
                continue
            start = 0
            page_chunk = 0
            while start < len(text):
                end = min(start + CHUNK_SIZE, len(text))
                fragment = text[start:end]
                if fragment.strip():
                    chunks.append(Chunk(
                        id=f"{document_id}_p{number:04d}_c{page_chunk:04d}",
                        document_id=document_id, page_number=number, text=fragment,
                        order=len(chunks), char_start=start, char_end=end,
                    ))
                    page_chunk += 1
                if end == len(text):
                    break
                start = end - CHUNK_OVERLAP
        if not chunks:
            raise IngestError("no_extractable_text", "未提取到文本。扫描型 PDF 暂不支持 OCR，请上传文本型 PDF。")
        return chunks, page_count, warnings, title
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError("invalid_pdf", "PDF 已损坏或无法解析，请检查文件后重试。") from exc


def ingest_pdf(content: bytes, filename: str, store: Store, settings: Settings,
               source: SeedPaper | None = None) -> IngestResult:
    safe_filename = Path(filename.replace("\\", "/")).name
    if not safe_filename.lower().endswith(".pdf"):
        raise IngestError("invalid_file_type", "仅支持 .pdf 文件。", 415)
    if not content:
        raise IngestError("empty_file", "文件为空，请重新选择 PDF。", 400)
    if len(content) > settings.max_upload_bytes:
        raise IngestError("file_too_large", f"文件超过 {settings.max_upload_mb} MB 限制。", 413)
    if not content.startswith(b"%PDF-"):
        raise IngestError("invalid_pdf", "文件内容不是有效 PDF，修改扩展名不能转换格式。")
    sha256 = hashlib.sha256(content).hexdigest()
    with INGEST_LOCK:
        existing = store.find_sha256(sha256)
        if existing:
            if not store.pdf_path(existing).is_file():
                raise IngestError("missing_pdf", "已导入记录的原文件缺失，请恢复本地数据目录。", 409)
            if source and not existing.source_url:
                existing = existing.model_copy(update={
                    "title": source.title, "authors": source.authors, "year": source.year,
                    "source_url": source.source_url, "source_pdf_url": source.pdf_url,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                })
                store.update_source(existing)
            return IngestResult(document=existing, duplicate=True)
        document_id = f"doc_{sha256[:24]}"
        chunks, page_count, warnings, pdf_title = parse_pdf(content, document_id, settings.max_pdf_pages)
        document = Document(
            id=document_id, title=source.title if source else (pdf_title or Path(safe_filename).stem),
            original_filename=safe_filename, authors=source.authors if source else [],
            year=source.year if source else None, source_url=source.source_url if source else None,
            source_pdf_url=source.pdf_url if source else None,
            retrieved_at=datetime.now(timezone.utc).isoformat() if source else None,
            sha256=sha256, page_count=page_count, chunk_count=len(chunks),
            ingest_status="ready_with_warnings" if warnings else "ready", warnings=warnings,
            created_at=datetime.now(timezone.utc).isoformat(), pdf_url=f"/api/documents/{document_id}/pdf",
        )
        target = store.pdf_path(document)
        temporary = target.with_suffix(".tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(target)
            store.save(document, chunks)
        except Exception:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise
        return IngestResult(document=document, duplicate=False)
