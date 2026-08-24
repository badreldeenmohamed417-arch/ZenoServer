from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from ..core.paths import storage_path

import sqlite_vec

from ..core.models import AuthorityLevel, Chunk, ContentType, SearchResult
from .base import VectorStore

log = logging.getLogger(__name__)

_FILTER_FIELDS = frozenset(
    {
        "subject",
        "grade",
        "term",
        "curriculum_year",
        "source_type",
        "document_id",
        "lesson",
        "content_type",
    }
)


def _md_text(value) -> str:
    return "" if value is None else str(value)


def _chunk_from_metadata(chunk_id: str, md: dict) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=md.get("document_id", ""),
        source_id=md.get("source_id", ""),
        subject=md.get("subject", ""),
        grade=md.get("grade", ""),
        term=md.get("term") or None,
        curriculum_year=md.get("curriculum_year") or None,
        authority=md.get("authority", AuthorityLevel.UNKNOWN),
        source_type=md.get("source_type", "other"),
        chapter=md.get("chapter"),
        lesson=md.get("lesson") or None,
        section=md.get("section"),
        page_start=int(md.get("page_start", 0)),
        page_end=int(md.get("page_end", 0)),
        content_type=md.get("content_type", ContentType.OTHER),
        content=md.get("content", ""),
        answered=md.get("answered"),
        token_estimate=max(1, len(md.get("content", "")) // 4),
        content_hash=hashlib.sha256(md.get("content", "").encode()).hexdigest(),
    )


def _filter_sql(filters: dict | None) -> tuple[str, list]:
    if not filters:
        return "", []

    clauses: list[str] = []
    params: list = []
    for key, value in filters.items():
        if key not in _FILTER_FIELDS:
            continue
        if isinstance(value, dict):
            if "$eq" in value:
                clauses.append(f"{key} = ?")
                params.append(_md_text(value["$eq"]))
            elif "$in" in value:
                items = list(value["$in"])
                if not items:
                    clauses.append("1 = 0")
                else:
                    placeholders = ",".join("?" * len(items))
                    clauses.append(f"{key} IN ({placeholders})")
                    params.extend(_md_text(v) for v in items)
        else:
            clauses.append(f"{key} = ?")
            params.append(_md_text(value))

    if not clauses:
        return "", []
    return " AND " + " AND ".join(clauses), params


class SQLiteVectorStore(VectorStore):
    """Production-ready local vector store backed by sqlite-vec KNN indexing."""

    def __init__(self, path: str | Path | None = None, dimension: int = 768):
        path = path or storage_path("vectors.db")
        self.path = Path(path)
        self.dimension = dimension
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute("DROP TABLE IF EXISTS vectors")
            conn.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                    chunk_id TEXT PRIMARY KEY,
                    embedding float[{self.dimension}] distance_metric=cosine,
                    document_id TEXT partition key,
                    subject TEXT,
                    grade TEXT,
                    term TEXT,
                    curriculum_year TEXT,
                    source_type TEXT,
                    lesson TEXT,
                    content_type TEXT,
                    +metadata_json TEXT
                )
                """
            )

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> str:
        if len(chunks) != len(embeddings):
            raise ValueError("count mismatch")
        if embeddings and len(embeddings[0]) != self.dimension:
            raise ValueError(
                f"embedding dimension {len(embeddings[0])} does not match store dimension {self.dimension}"
            )

        rows = []
        for chunk, vector in zip(chunks, embeddings):
            md = chunk.vector_metadata()
            rows.append(
                (
                    chunk.chunk_id,
                    sqlite_vec.serialize_float32(vector),
                    _md_text(md.get("document_id")),
                    _md_text(md.get("subject")),
                    _md_text(md.get("grade")),
                    _md_text(md.get("term")),
                    _md_text(md.get("curriculum_year")),
                    _md_text(md.get("source_type")),
                    _md_text(md.get("lesson")),
                    _md_text(md.get("content_type")),
                    json.dumps(md, ensure_ascii=False),
                )
            )

        with self._conn() as conn:
            chunk_ids = [(c.chunk_id,) for c in chunks]
            conn.executemany("DELETE FROM vec_chunks WHERE chunk_id = ?", chunk_ids)
            conn.executemany(
                """
                INSERT INTO vec_chunks(
                    chunk_id, embedding, document_id, subject, grade, term,
                    curriculum_year, source_type, lesson, content_type, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        log.info("SUCCESS sqlite upsert vectors=%d path=%s", len(chunks), self.path)
        return "local"

    def query(
        self, embedding: list[float], top_k: int = 10, filters: dict | None = None
    ) -> list[SearchResult]:
        if len(embedding) != self.dimension:
            raise ValueError(
                f"query embedding dimension {len(embedding)} does not match store dimension {self.dimension}"
            )

        filter_sql, filter_params = _filter_sql(filters)
        sql = f"""
            SELECT chunk_id, distance, metadata_json
            FROM vec_chunks
            WHERE embedding MATCH ?
              AND k = ?
              {filter_sql}
        """
        params = [sqlite_vec.serialize_float32(embedding), top_k, *filter_params]

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        out: list[SearchResult] = []
        for rank, row in enumerate(rows, 1):
            md = json.loads(row["metadata_json"])
            chunk = _chunk_from_metadata(row["chunk_id"], md)
            score = max(0.0, 1.0 - float(row["distance"]))
            out.append(SearchResult(chunk_id=row["chunk_id"], score=score, chunk=chunk, rank=rank))
        return out
