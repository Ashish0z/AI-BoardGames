from __future__ import annotations

import json
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaClient:
    def __init__(
        self,
        model: str = "gpt-oss:120b-cloud",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

    def chat(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        req = Request(
            url=f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urlopen(req, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return body.get("message", {}).get("content", "")
            except (URLError, socket.timeout, TimeoutError, HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                break

        raise RuntimeError("Unable to reach local Ollama service") from last_error
