import json
import os


def get_gateway_limits() -> str:
    """Expose live AI Gateway rate limits and semantic cache thresholds."""
    return json.dumps(
        {
            "rate_limit_rps": 50,
            "burst_limit": 100,
            "semantic_cache_threshold": 0.15,
            "l1_redis_ttl_seconds": 3600,
        },
        indent=2,
    )


def get_inference_metadata() -> str:
    """Expose active private vLLM model and air-gapped endpoint metadata."""
    return json.dumps(
        {
            "model": os.getenv("VLLM_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"),
            "endpoint": os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1"),
            "air_gapped": True,
        },
        indent=2,
    )