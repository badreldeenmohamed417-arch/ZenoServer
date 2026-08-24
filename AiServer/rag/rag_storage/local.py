from __future__ import annotations
import shutil
from pathlib import Path

class LocalStorageManager:
    """
    Manages storing original PDF documents and files on the server local filesystem under `storage/documents/`.
    """
    def __init__(self, base_dir: str | Path = "storage"):
        self.base_dir = Path(base_dir)
        self.documents_dir = self.base_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def save_document(self, local_path: str | Path, key: str | None = None) -> str:
        """
        Saves a local document file into server storage directory.
        Returns the relative path to the saved file (e.g. storage/documents/science.pdf).
        """
        src = Path(local_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        filename = key or src.name
        # Remove any leading directories in key if passed like 'documents/foo.pdf'
        filename = Path(filename).name

        dest = self.documents_dir / filename
        shutil.copy2(src, dest)
        return str(dest)
