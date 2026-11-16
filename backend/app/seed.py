import json

import httpx

from .config import MANIFEST_PATH, Settings
from .errors import IngestError
from .ingest import ingest_pdf
from .schemas import ApiError, SeedPaper, SeedResult
from .store import Store


def load_papers() -> list[SeedPaper]:
    return [SeedPaper.model_validate(item) for item in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))]


def import_paper(paper: SeedPaper, store: Store, settings: Settings) -> SeedResult:
    try:
        # URL comes exclusively from the checked-in manifest; no user-supplied URL fetching.
        with httpx.Client(timeout=settings.seed_timeout_seconds, follow_redirects=True) as client:
            with client.stream("GET", paper.pdf_url) as response:
                response.raise_for_status()
                size = 0
                parts: list[bytes] = []
                for part in response.iter_bytes(64 * 1024):
                    size += len(part)
                    if size > settings.max_upload_bytes:
                        raise IngestError("file_too_large", f"官方 PDF 超过 {settings.max_upload_mb} MB 限制。", 413)
                    parts.append(part)
        result = ingest_pdf(b"".join(parts), f"{paper.id}.pdf", store, settings, source=paper)
        return SeedResult(
            paper_id=paper.id, status="duplicate" if result.duplicate else "imported",
            document=result.document, manual_url=paper.source_url,
        )
    except IngestError as exc:
        error = ApiError(code=exc.code, message=exc.message)
    except httpx.HTTPError:
        error = ApiError(code="source_unavailable", message="官方来源访问失败或超时，请打开官方页面下载后手动上传。")
    return SeedResult(paper_id=paper.id, status="failed", error=error, manual_url=paper.source_url)
