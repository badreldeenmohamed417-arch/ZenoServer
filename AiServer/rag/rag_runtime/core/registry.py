from __future__ import annotations
import json, sqlite3
from pathlib import Path
from ..core.models import DocumentMetadata
from .paths import storage_path

class DocumentRegistry:
    def __init__(self,path:str|Path|None=None):
        path = path or storage_path("zeno.db")
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._init()
    def _conn(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS documents (document_id TEXT PRIMARY KEY, payload TEXT NOT NULL, file_hash TEXT, indexed_at TEXT)")
    def upsert(self,d:DocumentMetadata):
        with self._conn() as c: c.execute("INSERT INTO documents VALUES (?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET payload=excluded.payload,file_hash=excluded.file_hash,indexed_at=excluded.indexed_at",(d.document_id,d.model_dump_json(),d.file_hash,d.indexed_at))
    def get(self,document_id:str):
        with self._conn() as c: row=c.execute("SELECT payload FROM documents WHERE document_id=?",(document_id,)).fetchone()
        return DocumentMetadata.model_validate_json(row[0]) if row else None
    def list(self):
        with self._conn() as c: rows=c.execute("SELECT payload FROM documents ORDER BY document_id").fetchall()
        return [DocumentMetadata.model_validate_json(r[0]) for r in rows]
