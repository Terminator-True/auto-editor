"""Offline fake Ollama transports and an stdlib http.server fake.

``FakeTransport`` lets tests inject canned status/body or a synchronous
exception (URLError for connection-refused, socket.timeout for timeout) so
the ``OllamaClient`` never touches live ``localhost:11434``.

``FakeLLMTransport`` is the orchestrator's LLM seam: a ``generate`` that
returns a canned LLM JSON body (a valid ``LlmOutput``) or raises an injected
error, so the end-to-end pipeline runs fully offline.
"""

from __future__ import annotations

import json

# Canned, schema-valid LLM output with one in-range ``corte``.
VALID_LLM_BODY = json.dumps(
    {
        "segmento": {"inicio": "00:00:01:00", "fin": "00:00:14:00"},
        "acciones": [
            {"tipo": "corte", "rango": {"inicio": "00:00:05:00", "fin": "00:00:08:00"},
             "motivo": "intro"},
        ],
    }
)


class FakeTransport:
    """Deterministic transport returning a canned (status, body) tuple.

    ``error``, when set, is raised synchronously by ``post`` instead of
    returning a response (used to simulate connection-refused / timeout).
    """

    def __init__(self, status: int = 200, body: bytes = b"{}", error=None) -> None:
        self.status = status
        self.body = body
        self.error = error
        self.calls: list = []

    def post(self, url: str, json_body: dict, timeout: float) -> tuple:
        self.calls.append({"url": url, "json_body": json_body, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return self.status, self.body


class FakeLLMTransport:
    """Orchestrator LLM seam: returns a canned JSON body or raises an error.

    Mirrors ``OllamaClient.generate(prompt, system)`` at the transport seam so
    the orchestrator never touches a live Ollama endpoint.
    """

    def __init__(self, body: str = VALID_LLM_BODY, error=None) -> None:
        self.body = body
        self.error = error
        self.calls: list = []

    def generate(self, prompt: str, system: str = "") -> str:
        self.calls.append({"prompt": prompt, "system": system})
        if self.error is not None:
            raise self.error
        return self.body
