import sys
import os
import time

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pipeline.rag import RAGPipeline
except ImportError:
    # Try alternative import path
    from backend.pipeline.rag import RAGPipeline


def main():
    rag = RAGPipeline()
    queries = [
        "How do I set up SSO in Atlan?",
        "Where can I find API keys and rate limits?",
        "How to create a glossary term and attach it to assets?",
    ]
    for q in queries:
        print(f"\nQ: {q}")
        t0 = time.time()
        result = rag.get_rag_answer(q)
        dt = (time.time() - t0) * 1000
        if 'error' in result:
            print(f"Error: {result['error']}")
            continue
        print(f"Latency: {dt:.1f} ms")
        print("Answer:\n", result.get("answer", ""))
        print("Sources:", result.get("sources", []))


if __name__ == "__main__":
    main()






