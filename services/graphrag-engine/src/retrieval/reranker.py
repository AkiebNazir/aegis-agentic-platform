from typing import List, Tuple


def filter_and_rerank_vectors(
    vector_hits: List[Tuple[str, float]],
    max_distance: float = 0.65,
) -> List[str]:
    """Filters out noisy low-similarity chunks and returns ranked documents."""
    filtered = [(doc, dist) for doc, dist in vector_hits if dist <= max_distance]
    filtered.sort(key=lambda item: item[1])
    return [doc for doc, _ in filtered]


def synthesize_hybrid_context(graph_facts: List[str], vector_chunks: List[str]) -> str:
    """Combines Neo4j structural relationships with ChromaDB semantic chunks."""
    sections: List[str] = []

    if graph_facts:
        graph_block = "\n".join(f"- {fact}" for fact in graph_facts)
        sections.append(f"### Structural Service Topology (Neo4j)\n{graph_block}")

    if vector_chunks:
        vector_block = "\n".join(f"- {chunk}" for chunk in vector_chunks)
        sections.append(f"### Relevant Runbooks & Docs (ChromaDB)\n{vector_block}")

    if not sections:
        return "No relevant graph topology or vector runbooks found for this query."

    return "\n\n".join(sections)