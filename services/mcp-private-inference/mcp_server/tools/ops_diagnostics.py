import os
import httpx
import psutil

GO_BRIDGE_URL = os.getenv("GO_BRIDGE_URL", "http://localhost:8090")


def check_node_health() -> dict:
    """Inspect real-time host CPU, memory, and disk metrics for automated remediation."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "status": "HEALTHY",
    }


def inspect_backend_service(service_name: str) -> dict:
    """Query the Golang backend bridge for live microservice health and circuit-breaker state."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{GO_BRIDGE_URL}/internal/services/{service_name}/status")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        return {
            "service": service_name,
            "status": "BRIDGE_UNREACHABLE",
            "error": str(exc),
        }