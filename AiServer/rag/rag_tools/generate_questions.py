"""Create reviewable, deterministic question candidates from chunk metadata/content."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from rag_runtime.evaluation.retrieval import load_chunks


def candidate_for(chunk, number: int) -> dict:
    # This deliberately creates a review prompt, not asserted curriculum truth.
    # The reviewer replaces/refines it against the displayed source in review_questions.
    topic = (chunk.lesson or chunk.section or "هذا الجزء من المنهج").strip()
    return {
        "id": f"q_{number:06d}",
        "question": f"ما الفكرة العلمية الرئيسة التي يشرحها النص في {topic}؟",
        "subject": chunk.subject,
        "grade": chunk.grade,
        "term": chunk.term,
        "chapter": chunk.chapter or topic,
        "document_id": chunk.document_id,
        "expected_pages": list(range(chunk.page_start, chunk.page_end + 1)),
        "expected_chunk_ids": [chunk.chunk_id],
        "difficulty": "unknown",
        "tags": [topic],
        "verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate unverified retrieval-question candidates from chunks.")
    parser.add_argument("--chunks", required=True, help="Chunk JSONL file")
    parser.add_argument("--output", required=True, help="Question JSONL output")
    parser.add_argument("--append", action="store_true", help="Append instead of replacing output")
    args = parser.parse_args()
    chunks = load_chunks([Path(args.chunks)])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = 1
    if args.append and output.exists():
        start = sum(bool(line.strip()) for line in output.read_text(encoding="utf-8").splitlines()) + 1
    mode = "a" if args.append else "w"
    with output.open(mode, encoding="utf-8") as handle:
        for index, chunk in enumerate(chunks, start):
            handle.write(json.dumps(candidate_for(chunk, index), ensure_ascii=False) + "\n")
    print(f"Generated {len(chunks)} unverified candidates: {output}")


if __name__ == "__main__":
    main()
