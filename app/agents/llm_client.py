import os
import time
import httpx
from typing import Dict, Any, Optional


class LLMClient:
    """
    Shared LLM client with retry mechanism and observability
    """

    def __init__(self):
        self.base_url = os.getenv("ANTHROPIC_BASE_URL", "")
        self.token = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.max_retries = 3
        self.retry_delay = 1.0

    def chat(self, system: str, user: str, max_retries: int = None) -> str:
        """
        Chat with LLM and retry on failure
        """
        retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(retries):
            try:
                return self._call_llm(system, user)
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    print(
                        f"LLM call failed (attempt {attempt + 1}/{retries}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    print(f"LLM call failed after {retries} attempts: {e}")

        raise last_error

    def _call_llm(self, system: str, user: str) -> str:
        if not self.base_url or not self.token:
            raise Exception("LLM not configured")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        response = httpx.post(
            f"{self.base_url}/v1/messages", headers=headers, json=payload, timeout=60.0
        )

        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")

        result = response.json()
        return result["content"][0]["text"]


llm_client = LLMClient()
