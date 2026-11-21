import logging
from mcp.server.fastmcp import FastMCP

from mcp_server.tools.ops_diagnostics import check_node_health, inspect_backend_service
from mcp_server.tools.graph_query_tool import query_architecture_graph
from mcp_server.resources.config import get_gateway_limits, get_inference_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegis.mcp.server")

mcp = FastMCP("Aegis-Enterprise-MCP")


@mcp.tool()
def tool_check_node_health() -> dict:
    """Check host CPU, memory, and disk telemetry."""
    logger.info("MCP Tool invoked: tool_check_node_health")
    return check_node_health()


@mcp.tool()
def tool_inspect_backend_service(service_name: str) -> dict:
    """Inspect a downstream Golang/Python microservice via the internal Go bridge."""
    logger.info("MCP Tool invoked: tool_inspect_backend_service(%s)", service_name)
    return inspect_backend_service(service_name)


@mcp.tool()
def tool_query_architecture_graph(question: str) -> str:
    """Query Neo4j service topology and ChromaDB runbooks via Hybrid GraphRAG."""
    logger.info("MCP Tool invoked: tool_query_architecture_graph(%s)", question)
    return query_architecture_graph(question)


@mcp.resource("config://aegis/gateway-limits")
def resource_gateway_limits() -> str:
    """Live AI Gateway rate-limit and semantic cache thresholds."""
    return get_gateway_limits()


@mcp.resource("config://aegis/inference-model")
def resource_inference_model() -> str:
    """Active private vLLM model metadata."""
    return get_inference_metadata()


if __name__ == "__main__":
    # Supports stdio (default for local MCP clients) or streamable-http for containerized agents
    mcp.run()