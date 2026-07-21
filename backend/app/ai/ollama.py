from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen


class OllamaClient:
    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

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
        try:
            with urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body.get("message", {}).get("content", "")
        except URLError as exc:
            raise RuntimeError("Unable to reach local Ollama service") from exc
