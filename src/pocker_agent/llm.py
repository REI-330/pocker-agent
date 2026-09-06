from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelClient(Protocol):
    def complete(self, messages: list[dict[str, str]], *, response_format: dict[str, Any] | None = None) -> str: ...


@dataclass
class OpenAICompatibleClient:
    """Minimal Chat Completions client; works with OpenAI-compatible gateways."""

    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        return cls(
            api_key=os.getenv("POCKER_AGENT_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            model=os.getenv("POCKER_AGENT_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("POCKER_AGENT_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        )

    def complete(self, messages: list[dict[str, str]], *, response_format: dict[str, Any] | None = None) -> str:
        if not self.api_key:
            raise RuntimeError("missing_model_api_key: set POCKER_AGENT_API_KEY or OPENAI_API_KEY")
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0}
        if response_format:
            payload["response_format"] = response_format
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"model_request_failed: {error}") from error
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("model_response_invalid: missing choices[0].message.content") from error
