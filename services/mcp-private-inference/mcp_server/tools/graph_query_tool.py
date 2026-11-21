import os
import httpx

GRAPHRAG_HTTP_URL = os.getenv("GRAPHRAG_HTTP_URL", "http://localhost:8003")


def query_architecture_graph(question: str) -> str:
    """Retrieve service dependency topology (Neo4j) and runbooks (ChromaDB) via GraphRAG."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{GRAPHRAG_HTTP_URL}/v1/retrieve",
                json={"query": question},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("merged_context", "No graph or vector context found.")
    except Exception as exc:
        return f"GraphRAG service unavailable ({exc}). Verify graphrag-engine is running."