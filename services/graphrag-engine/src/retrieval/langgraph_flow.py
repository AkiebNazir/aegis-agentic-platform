from typing import TypedDict, List, Tuple
from langgraph.graph import StateGraph, START, END

from src.ingestion.graph_loader import Neo4jGraphLoader
from src.ingestion.vector_loader import ChromaVectorLoader
from src.retrieval.reranker import filter_and_rerank_vectors, synthesize_hybrid_context


class GraphRAGState(TypedDict):
    query: str
    top_k: int
    raw_vector_hits: List[Tuple[str, float]]
    vector_chunks: List[str]
    graph_facts: List[str]
    merged_context: str


class HybridGraphRAGWorkflow:
    """LangGraph workflow unifying Neo4j graph traversal and ChromaDB vector search."""

    def __init__(self, graph_loader: Neo4jGraphLoader, vector_loader: ChromaVectorLoader):
        self.graph_loader = graph_loader
        self.vector_loader = vector_loader
        self.app = self._build_graph()

    def _vector_search_node(self, state: GraphRAGState) -> dict:
        hits = self.vector_loader.search(state["query"], top_k=state["top_k"])
        ranked = filter_and_rerank_vectors(hits)
        return {"raw_vector_hits": hits, "vector_chunks": ranked}

    def _graph_traversal_node(self, state: GraphRAGState) -> dict:
        facts = self.graph_loader.query_related_topology(state["query"])
        return {"graph_facts": facts}

    def _synthesize_node(self, state: GraphRAGState) -> dict:
        merged = synthesize_hybrid_context(
            state.get("graph_facts", []),
            state.get("vector_chunks", []),
        )
        return {"merged_context": merged}

    def _build_graph(self):
        builder = StateGraph(GraphRAGState)
        builder.add_node("vector_search", self._vector_search_node)
        builder.add_node("graph_traversal", self._graph_traversal_node)
        builder.add_node("synthesize", self._synthesize_node)

        # Run vector search and graph traversal, then synthesize
        builder.add_edge(START, "vector_search")
        builder.add_edge("vector_search", "graph_traversal")
        builder.add_edge("graph_traversal", "synthesize")
        builder.add_edge("synthesize", END)
        return builder.compile()

    def retrieve(self, query: str, top_k: int = 3) -> GraphRAGState:
        initial: GraphRAGState = {
            "query": query,
            "top_k": top_k,
            "raw_vector_hits": [],
            "vector_chunks": [],
            "graph_facts": [],
            "merged_context": "",
        }
        return self.app.invoke(initial)