"""Interactive source-ground-truth review for generated question JSONL."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from rag_runtime.evaluation.retrieval import load_chunks


def edit(question: dict) -> None:
    for field in ("question", "subject", "grade", "term", "chapter", "difficulty"):
        value = input(f"{field} [{question.get(field, '')}]: ").strip()
        if value:
            question[field] = value
    pages = input(f"expected_pages comma-separated [{','.join(map(str, question['expected_pages']))}]: ").strip()
    if pages:
        question["expected_pages"] = [int(x.strip()) for x in pages.split(",") if x.strip()]
    chunks = input(f"expected_chunk_ids comma-separated [{','.join(question['expected_chunk_ids'])}]: ").strip()
    if chunks:
        question["expected_chunk_ids"] = [x.strip() for x in chunks.split(",") if x.strip()]
    tags = input(f"tags comma-separated [{','.join(question.get('tags', []))}]: ").strip()
    if tags:
        question["tags"] = [x.strip() for x in tags.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Review retrieval-question ground truth against source chunks.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--chunks", action="append", help="Chunk JSONL (repeatable); defaults to storage/<document_id>.chunks.jsonl")
    args = parser.parse_args()
    path = Path(args.input)
    questions = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunk_paths = [Path(value) for value in args.chunks] if args.chunks else sorted({Path("storage") / f"{q['document_id']}.chunks.jsonl" for q in questions})
    missing = [str(value) for value in chunk_paths if not value.exists()]
    if missing:
        parser.error("chunk source files not found: " + ", ".join(missing) + "; pass --chunks explicitly")
    by_id = {chunk.chunk_id: chunk for chunk in load_chunks(chunk_paths)}
    changed = False
    for question in questions:
        print("\n" + "-" * 60 + "\nQUESTION\n" + "-" * 60)
        print(question.get("question", ""))
        print("\nEXPECTED PAGES:\n" + ", ".join(map(str, question.get("expected_pages", []))))
        print("\nEXPECTED CHUNKS:\n" + ", ".join(question.get("expected_chunk_ids", [])))
        print("\nSOURCE:")
        for chunk_id in question.get("expected_chunk_ids", []):
            chunk = by_id.get(chunk_id)
            print(f"\n[{chunk_id}]\n{chunk.content if chunk else 'MISSING CHUNK'}")
        while True:
            choice = input("\n[y] Accept  [n] Reject  [e] Edit  [s] Skip  [q] Quit: ").strip().lower()
            if choice == "y": question["verified"] = True; changed = True; break
            if choice == "n": question["verified"] = False; changed = True; break
            if choice == "e": edit(question); changed = True; continue
            if choice == "s": break
            if choice == "q":
                path.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
                return
    if changed:
        path.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
