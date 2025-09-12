import argparse
import json
import time
import sys
import os
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pipeline.rag import RAGPipeline
except ImportError:
    # Try alternative import path
    from backend.pipeline.rag import RAGPipeline


def load_eval_queries(path: str) -> List[Dict[str, Any]]:
    """Load evaluation queries from JSON file."""
    # Handle relative paths from the backend directory
    if not os.path.isabs(path) and path.startswith('backend/'):
        path = path.replace('backend/', '')
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Evaluation file must be a list of objects: {question, expected_keywords, allow_empty?}")
    return data


def contains_any(text: str, keywords: List[str]) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG answers for precision, citations, and latency")
    parser.add_argument("--eval_file", default="backend/data/rag_eval.json", help="Path to eval questions JSON")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of eval items (0 = all)")
    args = parser.parse_args()

    # Initialize pipeline once
    rag = RAGPipeline()

    queries = load_eval_queries(args.eval_file)
    if args.limit > 0:
        queries = queries[: args.limit]

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []
    pass_count = 0
    citation_pass = 0

    for i, item in enumerate(queries, 1):
        question: str = item.get("question", "").strip()
        expected_keywords: List[str] = item.get("expected_keywords", [])
        allow_empty: bool = bool(item.get("allow_empty", False))

        start = time.time()
        rag_result = rag.get_rag_answer(question)
        latency = time.time() - start
        latencies.append(latency)

        error = rag_result.get("error")
        answer = rag_result.get("answer", "")
        sources = rag_result.get("sources", [])

        # Basic correctness heuristic: expected keywords appear
        has_keywords = contains_any(answer, expected_keywords) if expected_keywords else bool(answer)

        # If no context found, answer may be fallback text; allow_empty controls this
        if not allow_empty:
            passed = has_keywords and bool(sources)
        else:
            passed = bool(sources) or has_keywords

        if passed:
            pass_count += 1
        if sources:
            citation_pass += 1

        results.append({
            "index": i,
            "question": question,
            "latency_ms": round(latency * 1000, 1),
            "error": error,
            "has_sources": bool(sources),
            "num_sources": len(sources),
            "passed_keywords_check": has_keywords,
            "passed": passed,
            "answer_preview": answer[:300]
        })

    total = len(queries)
    avg_latency_ms = round(sum(latencies) / total * 1000, 1) if total else 0.0
    summary = {
        "total": total,
        "passed": pass_count,
        "pass_rate": round((pass_count / total) * 100, 1) if total else 0.0,
        "citation_rate": round((citation_pass / total) * 100, 1) if total else 0.0,
        "avg_latency_ms": avg_latency_ms,
    }

    print("\n=== RAG Evaluation Summary ===")
    print(json.dumps(summary, indent=2))
    print("\n=== Detailed Results (first 5) ===")
    for r in results[:5]:
        print(json.dumps(r, indent=2))

    # Generate report
    report_path = args.eval_file.replace(".json", "_report.json")
    # Handle relative paths from the backend directory
    if not os.path.isabs(report_path) and report_path.startswith('backend/'):
        report_path = report_path.replace('backend/', '')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    # Save detailed report next to eval file
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(f"\nSaved detailed report to: {report_path}")


if __name__ == "__main__":
    main()






