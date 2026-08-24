"""Evaluate Zeno retrieval against manually verified chunk/page ground truth."""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

from rag_runtime.embeddings.sentence_transformers import SentenceTransformerEmbeddingProvider
from rag_runtime.evaluation.retrieval import (InMemoryCosineStore, aggregate, load_chunks,
    load_or_embed_chunks, load_or_embed_questions, score_retrieval, CachedQueryEmbeddingProvider)
from rag_runtime.retrieval.retriever import Retriever

REQUIRED = {"id", "question", "subject", "grade", "document_id", "expected_pages", "expected_chunk_ids", "verified"}


def load_questions(path: Path) -> tuple[list[dict], list[dict]]:
    valid, malformed = [], []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            missing = REQUIRED - set(value)
            if missing or not isinstance(value["expected_pages"], list) or not isinstance(value["expected_chunk_ids"], list):
                raise ValueError(f"missing/invalid fields: {', '.join(sorted(missing))}")
            if not value["id"] or not value["question"].strip() or not value["expected_pages"] or not value["expected_chunk_ids"]:
                raise ValueError("id, question, expected_pages, and expected_chunk_ids must be non-empty")
        except Exception as exc:
            malformed.append({"line": number, "error": str(exc), "raw": line})
            continue
        if value["verified"] is True:
            valid.append(value)
    return valid, malformed


def group_summary(results: list[dict], field: str) -> dict:
    groups = defaultdict(list)
    for result in results:
        groups[str(result.get(field, "unknown"))].append(result)
    return {key: aggregate(value) for key, value in sorted(groups.items())}


def build_result(question: dict, retrieved, metrics: dict) -> dict:
    return {
        "question_id": question["id"], "question": question["question"],
        "document_id": question["document_id"], "subject": question["subject"],
        "chapter": question.get("chapter"), "difficulty": question.get("difficulty", "unknown"),
        "expected_chunk_ids": question["expected_chunk_ids"], "expected_pages": question["expected_pages"],
        "retrieved": [{"rank": row.rank, "chunk_id": row.chunk_id, "score": round(row.score, 6),
                       "page_start": row.chunk.page_start, "page_end": row.chunk.page_end,
                       "hit": row.chunk_id in question["expected_chunk_ids"]} for row in retrieved],
        "metrics": metrics,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ground-truth retrieval evaluation without an LLM.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--chunks", action="append", help="Chunk JSONL (repeatable)")
    source.add_argument("--chunks-dir", help="Directory containing *.chunks.jsonl")
    parser.add_argument("--questions", required=True)
    parser.add_argument("--model", default="sayed0am/arabic-english-bge-m3")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output-dir", default="storage/evaluation")
    args = parser.parse_args()
    if args.top_k < 1: parser.error("--top-k must be at least 1")
    question_path, output_dir = Path(args.questions), Path(args.output_dir)
    paths = [Path(x) for x in args.chunks] if args.chunks else sorted(Path(args.chunks_dir).glob("*.chunks.jsonl"))
    if not paths: parser.error("no chunk files found")

    questions, malformed = load_questions(question_path)
    print("Loading model...")
    provider = SentenceTransformerEmbeddingProvider(args.model, batch_size=args.batch_size)
    print("Loading chunks...")
    chunks = load_chunks(paths)
    chunk_ids = {chunk.chunk_id for chunk in chunks}
    bad_ground_truth = [q["id"] for q in questions if not set(q["expected_chunk_ids"]).issubset(chunk_ids)]
    if bad_ground_truth:
        raise SystemExit(f"Verified questions reference chunks not in supplied datasets: {', '.join(bad_ground_truth)}")
    embeddings = load_or_embed_chunks(paths, chunks, provider, output_dir / "embeddings")
    question_embeddings = load_or_embed_questions(question_path, questions, provider, output_dir / "embeddings")
    store = InMemoryCosineStore(chunks, embeddings)

    results = []
    for index, (question, vector) in enumerate(zip(questions, question_embeddings), 1):
        # Reuse Retriever.search while supplying the cached question vector.
        retriever = Retriever(CachedQueryEmbeddingProvider(vector), store)
        rows = retriever.search(question["question"], top_k=args.top_k, filters={"document_id": question["document_id"]})
        metrics = score_retrieval(question, rows)
        results.append(build_result(question, rows, metrics))
        print(f"Evaluating {index}/{len(questions)}")

    failures = [r for r in results if not r["metrics"]["hit_at_10"]]
    summary = aggregate(results)
    summary["verified_questions"] = len(questions)
    summary["malformed_questions"] = len(malformed)
    report = {"summary": summary, "by_subject": group_summary(results, "subject"),
              "by_chapter": group_summary(results, "chapter"), "by_difficulty": group_summary(results, "difficulty"),
              "failures": [r["question_id"] for r in failures], "malformed_questions": malformed}
    write_jsonl(output_dir / "results.jsonl", results)
    write_jsonl(output_dir / "failures.jsonl", failures)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + "=" * 60 + "\nZENO RAG EVALUATION\n" + "=" * 60)
    print(f"Questions evaluated: {summary['questions']}\nVerified questions: {summary['verified_questions']}\nFailed questions: {summary['failed_questions']}")
    for key, label in (("recall_at_1", "Recall@1"), ("recall_at_3", "Recall@3"), ("recall_at_5", "Recall@5"), ("recall_at_10", "Recall@10")):
        print(f"{label}: {summary[key] * 100:.1f}%")
    print(f"MRR: {summary['mrr']:.3f}\nAverage top-1 similarity: {summary['average_top_1_similarity']:.4f}\nAverage top-5 similarity: {summary['average_top_5_similarity']:.4f}")
    print("Evaluation complete.")


if __name__ == "__main__":
    main()
