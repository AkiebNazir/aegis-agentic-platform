import os
import time
import threading
import logging
from concurrent import futures

import grpc
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from src import graphrag_pb2, graphrag_pb2_grpc
from src.ingestion.graph_loader import Neo4jGraphLoader
from src.ingestion.vector_loader import ChromaVectorLoader
from src.retrieval.langgraph_flow import HybridGraphRAGWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.graphrag")

# Initialize shared workflow
graph_loader = Neo4jGraphLoader()
vector_loader = ChromaVectorLoader()
workflow = HybridGraphRAGWorkflow(graph_loader, vector_loader)


# --- gRPC Service (consumed by agent-orchestrator) ---
class GraphRAGServicer(graphrag_pb2_grpc.GraphRAGEngineServicer):
    def RetrieveContext(self, request, context):
        start = time.time()
        top_k = request.top_k if request.top_k > 0 else 3
        result = workflow.retrieve(request.query, top_k=top_k)

        return graphrag_pb2.RetrieveResponse(
            merged_context=result["merged_context"],
            graph_facts=result["graph_facts"],
            vector_chunks=result["vector_chunks"],
            latency_ms=(time.time() - start) * 1000,
        )


# --- HTTP Bridge (consumed by mcp-private-inference) ---
http_app = FastAPI(title="Aegis GraphRAG HTTP Bridge")


class RetrieveHTTPRequest(BaseModel):
    query: str
    top_k: int = 3


@http_app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "graphrag-engine"}


@http_app.post("/v1/retrieve")
def retrieve_http(req: RetrieveHTTPRequest):
    start = time.time()
    result = workflow.retrieve(req.query, top_k=req.top_k)
    return {
        "merged_context": result["merged_context"],
        "graph_facts": result["graph_facts"],
        "vector_chunks": result["vector_chunks"],
        "latency_ms": round((time.time() - start) * 1000, 2),
    }


def start_http_bridge(port: int) -> None:
    uvicorn.run(http_app, host="0.0.0.0", port=port, log_level="warning")


def serve() -> None:
    grpc_port = os.getenv("GRPC_PORT", "50052")
    http_port = int(os.getenv("HTTP_PORT", "8003"))

    # Seed sample data on startup if enabled
    if os.getenv("AUTO_SEED", "true").lower() == "true":
        try:
            graph_loader.seed_topology()
            vector_loader.seed_runbooks()
            logger.info("Seeded Neo4j topology and ChromaDB runbooks.")
        except Exception as exc:
            logger.warning("Auto-seed skipped (stores may still be starting): %s", exc)

    http_thread = threading.Thread(target=start_http_bridge, args=(http_port,), daemon=True)
    http_thread.start()
    logger.info("GraphRAG HTTP bridge listening on :%d", http_port)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    graphrag_pb2_grpc.add_GraphRAGEngineServicer_to_server(GraphRAGServicer(), server)
    server.add_insecure_port(f"[::]:{grpc_port}")
    logger.info("GraphRAG gRPC server listening on :%s", grpc_port)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()