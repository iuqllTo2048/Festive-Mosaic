import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .schemas import Chunk, ChunkPage, Document, QueryResult


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.pdf_dir = data_dir / "pdfs"
        self.db_path = data_dir / "evidence.sqlite3"

    @contextmanager
    def connect(self):
        with sqlite3.connect(self.db_path, timeout=30) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection

    def initialize(self) -> None:
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    original_filename TEXT NOT NULL, authors TEXT NOT NULL,
                    year INTEGER, source_url TEXT, source_pdf_url TEXT,
                    retrieved_at TEXT, sha256 TEXT NOT NULL UNIQUE,
                    page_count INTEGER NOT NULL, chunk_count INTEGER NOT NULL,
                    ingest_status TEXT NOT NULL, warnings TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(id),
                    page_number INTEGER NOT NULL, text TEXT NOT NULL,
                    chunk_order INTEGER NOT NULL,
                    char_start INTEGER NOT NULL, char_end INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS chunks_document_page
                    ON chunks(document_id, page_number, chunk_order);
                CREATE TABLE IF NOT EXISTS query_runs (
                    id TEXT PRIMARY KEY, result_json TEXT NOT NULL
                );
            """)

    @staticmethod
    def _document(row: sqlite3.Row) -> Document:
        values = dict(row)
        values["authors"] = json.loads(values["authors"])
        values["warnings"] = json.loads(values["warnings"])
        values["pdf_url"] = f"/api/documents/{values['id']}/pdf"
        return Document(**values)

    def list_documents(self) -> list[Document]:
        with self.connect() as db:
            return [self._document(row) for row in db.execute(
                "SELECT * FROM documents ORDER BY created_at DESC, id"
            )]

    def get_document(self, document_id: str) -> Document | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return self._document(row) if row else None

    def find_sha256(self, sha256: str) -> Document | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE sha256 = ?", (sha256,)).fetchone()
        return self._document(row) if row else None

    def save(self, document: Document, chunks: list[Chunk]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (document.id, document.title, document.original_filename,
                 json.dumps(document.authors, ensure_ascii=False), document.year,
                 document.source_url, document.source_pdf_url, document.retrieved_at,
                 document.sha256, document.page_count,
                 document.chunk_count, document.ingest_status,
                 json.dumps(document.warnings, ensure_ascii=False), document.created_at),
            )
            db.executemany("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)", [
                (chunk.id, chunk.document_id, chunk.page_number, chunk.text,
                 chunk.order, chunk.char_start, chunk.char_end) for chunk in chunks
            ])

    def update_source(self, document: Document) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE documents SET title=?, authors=?, year=?, source_url=?, "
                "source_pdf_url=?, retrieved_at=? WHERE id=?",
                (document.title, json.dumps(document.authors, ensure_ascii=False), document.year,
                 document.source_url, document.source_pdf_url, document.retrieved_at, document.id),
            )

    def list_chunks(self, document_id: str, page: int | None, offset: int, limit: int) -> ChunkPage:
        query = "FROM chunks WHERE document_id = ?"
        args: list[str | int] = [document_id]
        if page is not None:
            query += " AND page_number = ?"
            args.append(page)
        with self.connect() as db:
            total = db.execute("SELECT COUNT(*) " + query, args).fetchone()[0]
            rows = db.execute(
                "SELECT id, document_id, page_number, text, chunk_order AS 'order', "
                "char_start, char_end " + query + " ORDER BY chunk_order LIMIT ? OFFSET ?",
                [*args, limit, offset],
            ).fetchall()
        return ChunkPage(items=[Chunk(**dict(row)) for row in rows], total=total, offset=offset, limit=limit)

    def pdf_path(self, document: Document) -> Path:
        # Only server-generated hashes are used as filenames, never request paths.
        return self.pdf_dir / f"{document.sha256}.pdf"

    def retrieval_chunks(self, document_ids: list[str] | None) -> list[Chunk]:
        sql = "SELECT id, document_id, page_number, text, chunk_order AS 'order', char_start, char_end FROM chunks"
        args = document_ids or []
        if document_ids:
            sql += " WHERE document_id IN (" + ",".join("?" for _ in document_ids) + ")"
        with self.connect() as db:
            rows = db.execute(sql + " ORDER BY document_id, chunk_order", args).fetchall()
        return [Chunk(**dict(row)) for row in rows]

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT id, document_id, page_number, text, chunk_order AS 'order', char_start, char_end "
                "FROM chunks WHERE id = ?", (chunk_id,),
            ).fetchone()
        return Chunk(**dict(row)) if row else None

    def save_run(self, result: QueryResult) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO query_runs VALUES (?, ?)", (result.run_id, result.model_dump_json()))

    def get_run(self, run_id: str) -> QueryResult | None:
        with self.connect() as db:
            row = db.execute("SELECT result_json FROM query_runs WHERE id = ?", (run_id,)).fetchone()
        return QueryResult.model_validate_json(row[0]) if row else None
