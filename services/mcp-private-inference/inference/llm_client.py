import os
import time
import logging
from typing import List, Dict
from openai import OpenAI, APIConnectionError, APITimeoutError

logger = logging.getLogger("aegis.inference")


class PrivateLLMClient:
    """OpenAI-compatible client for air-gapped vLLM / Hugging Face inference."""

    def __init__(self):
        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
        self.api_key = os.getenv("VLLM_API_KEY", "local-vllm-airgapped")
        self.model = os.getenv("VLLM_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
        self.max_retries = int(os.getenv("VLLM_MAX_RETRIES", "3"))

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=30.0,
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        backoff = 0.5
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
            except (APIConnectionError, APITimeoutError) as exc:
                logger.warning(
                    "vLLM inference attempt %d/%d failed: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt == self.max_retries:
                    return (
                        f"[Fallback Mode: Private vLLM endpoint ({self.base_url}) unreachable "
                        f"after {self.max_retries} attempts]"
                    )
                time.sleep(backoff)
                backoff *= 2