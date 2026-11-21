import os
import time
import logging
from concurrent import futures
import grpc

from src import gateway_pb2, gateway_pb2_grpc
from src import graphrag_pb2, graphrag_pb2_grpc
from src.evaluator.judge_loop import EvaluatorOptimizerGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.agent-orchestrator")


class AgentOrchestratorServicer(gateway_pb2_grpc.AgentOrchestratorServicer):
    def __init__(self):
        self.graphrag_addr = os.getenv("GRAPHRAG_GRPC_ADDR", "localhost:50052")
        self.workflow = EvaluatorOptimizerGraph(max_retries=2)

    def _fetch_graphrag_context(self, query: str) -> str:
        try:
            with grpc.insecure_channel(self.graphrag_addr) as channel:
                stub = graphrag_pb2_grpc.GraphRAGEngineStub(channel)
                resp = stub.RetrieveContext(
                    graphrag_pb2.RetrieveRequest(query=query, top_k=3),
                    timeout=5.0,
                )
                return resp.merged_context
        except Exception as exc:
            logger.warning("GraphRAG gRPC call failed (%s): %s", self.graphrag_addr, exc)
            return "GraphRAG context unavailable."

    def ProcessPrompt(self, request, context):
        start = time.time()
        rag_context = (
            self._fetch_graphrag_context(request.prompt)
            if request.use_graph_rag
            else "No external GraphRAG context requested."
        )

        final_state = self.workflow.execute(
            request_id=request.request_id,
            prompt=request.prompt,
            context=rag_context,
        )

        source_tag = f"{final_state['agent_trace']} [eval:{final_state['evaluation_status']}]"
        return gateway_pb2.PromptResponse(
            answer=final_state["draft_answer"],
            cache_hit=False,
            source_agent=source_tag,
            latency_ms=(time.time() - start) * 1000,
        )


def serve() -> None:
    port = os.getenv("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    gateway_pb2_grpc.add_AgentOrchestratorServicer_to_server(
        AgentOrchestratorServicer(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    logger.info("agent-orchestrator gRPC server listening on :%s", port)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()