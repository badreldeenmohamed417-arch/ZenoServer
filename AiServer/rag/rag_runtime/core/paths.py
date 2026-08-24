from __future__ import annotations

import os
from pathlib import Path


def server_root() -> Path:
    """Return the current ZenoServer project directory."""
    configured = os.getenv("ZENO_SERVER_ROOT")
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[2]


def storage_root() -> Path:
    configured = os.getenv("ZENO_RAG_STORAGE_DIR")
    return (Path(configured).expanduser() if configured else server_root() / "rag_storage").resolve()


def storage_path(*parts: str) -> Path:
    return storage_root().joinpath(*parts)
