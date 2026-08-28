"""Offline fake Ollama transports and an stdlib http.server fake.

``FakeTransport`` lets tests inject canned status/body or a synchronous
exception (URLError for connection-refused, socket.timeout for timeout) so
the ``OllamaClient`` never touches live ``localhost:11434``.
"""

from __future__ import annotations


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
