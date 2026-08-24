#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_ROOT / "project_dump.txt"

# Directories that should never be included.
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

# Binary / generated files that are not useful inside a text dump.
EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pdf",
    ".npz",
    ".zip",
    ".gz",
    ".tar",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp3",
    ".mp4",
    ".wav",
    ".bin",
}

# Text-like files we explicitly allow even if they have no extension.
TEXT_FILENAMES = {
    "README",
    "LICENSE",
    "Makefile",
    "Dockerfile",
}


def is_binary_file(path: Path) -> bool:
    """
    Detect binary files conservatively.

    We read a small chunk and look for NUL bytes.
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
    except OSError:
        return True

    return b"\x00" in chunk


def should_skip(path: Path) -> bool:
    """
    Decide whether a file should be excluded from the dump.
    """
    if path.resolve() == OUTPUT_FILE.resolve():
        return True

    if path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True

    if path.name in TEXT_FILENAMES:
        return False

    # Skip files that are clearly binary.
    return is_binary_file(path)


def collect_files(root: Path) -> list[Path]:
    """
    Collect readable files while preserving the project's directory tree.
    """
    files: list[Path] = []

    for current_root, dirs, filenames in os.walk(root):
        current_path = Path(current_root)

        # Prevent os.walk from descending into excluded directories.
        dirs[:] = sorted(
            d for d in dirs
            if d not in EXCLUDED_DIRS
        )

        for filename in sorted(filenames):
            path = current_path / filename

            if should_skip(path):
                continue

            files.append(path)

    return sorted(
        files,
        key=lambda p: p.relative_to(root).as_posix().lower(),
    )


def build_tree(root: Path, files: list[Path]) -> str:
    """
    Build a simple tree section from the collected files.
    """
    lines: list[str] = [root.name, "."]

    # Only files that are actually going into the dump.
    relative_paths = [
        p.relative_to(root).as_posix()
        for p in files
    ]

    for rel in relative_paths:
        parts = rel.split("/")

        indent = ""
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                lines.append(f"{indent}└── {part}")
            else:
                lines.append(f"{indent}├── {part}")
                indent += "│   "

    return "\n".join(lines)


def write_dump(root: Path, files: list[Path]) -> None:
    """
    Write the complete project dump to project_dump.txt.
    """
    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as out:

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------
        out.write("=" * 100 + "\n")
        out.write("ZenoServer Project Dump\n")
        out.write("=" * 100 + "\n\n")

        out.write("PROJECT ROOT\n")
        out.write(f"{root}\n\n")

        out.write("PROJECT TREE\n")
        out.write("-" * 100 + "\n")
        out.write(build_tree(root, files))
        out.write("\n")
        out.write("-" * 100 + "\n\n")

        # ----------------------------------------------------
        # Files
        # ----------------------------------------------------
        out.write("FILE CONTENTS\n")
        out.write("=" * 100 + "\n\n")

        for index, path in enumerate(files, start=1):
            relative_path = path.relative_to(root).as_posix()

            out.write("\n")
            out.write("#" * 100 + "\n")
            out.write(f"# FILE {index}/{len(files)}\n")
            out.write(f"# PATH: {relative_path}\n")
            out.write("#" * 100 + "\n\n")

            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as exc:
                out.write(
                    f"[ERROR READING FILE: {exc}]\n"
                )
                continue

            out.write(content)

            if content and not content.endswith("\n"):
                out.write("\n")

            out.write("\n")

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------
        out.write("\n")
        out.write("=" * 100 + "\n")
        out.write("SUMMARY\n")
        out.write("=" * 100 + "\n")
        out.write(f"Files included: {len(files)}\n")


def main() -> None:
    files = collect_files(PROJECT_ROOT)
    write_dump(PROJECT_ROOT, files)

    print(
        f"Project dump created successfully:\n"
        f"{OUTPUT_FILE}\n"
        f"Files included: {len(files)}"
    )


if __name__ == "__main__":
    main()
