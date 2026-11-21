import os
from typing import List, Tuple
import chromadb
from sentence_transformers import SentenceTransformer


class ChromaVectorLoader:
    """Manages ChromaDB vector embeddings for runbooks and architecture docs."""

    def __init__(self, collection_name: str = "aegis_runbooks"):
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        self.client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = SentenceTransformer(model_name)

    def seed_runbooks(self) -> None:
        """Seeds operational runbooks into ChromaDB."""
        docs = [
            "RUNBOOK-104: PaymentGateway P99 latency spikes above 1500ms when the downstream FraudEngine gRPC connection pool saturates.",
            "REMEDIATION-104: Scale FraudEngine replicas via kubectl and increase gRPC max_concurrent_streams to 500.",
            "RUNBOOK-201: LoyaltyBenefitService experiences elevated error rates when SessionRedis memory fragmentation exceeds 85%.",
            "DB-POLICY: LedgerPostgres connections must route through PgBouncer to prevent connection exhaustion during peak traffic.",
        ]
        ids = ["rb-104", "rem-104", "rb-201", "db-pol"]
        embeddings = self.embedder.encode(docs).tolist()
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=docs)

    def search(self, query_text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Returns (document, cosine_distance) pairs ordered by semantic similarity."""
        q_vec = self.embedder.encode(query_text).tolist()
        res = self.collection.query(query_embeddings=[q_vec], n_results=top_k)

        docs = res.get("documents", [[]])[0]
        distances = res.get("distances", [[]])[0]
        return list(zip(docs, distances))