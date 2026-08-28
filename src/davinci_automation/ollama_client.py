"""Local Ollama HTTP client with injectable transport.

Zero new dependencies (stdlib ``urllib``) behind an injectable
``Transport.post`` seam so the probe runs fully offline against a fake
server. Loads a versioned prompt template from a configurable path, POSTs a
non-streaming request to ``/api/generate``, verifies the response, and
measures per-request latency (wall-clock + Ollama timing fields).
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Protocol, Tuple

# Default prompt template location, resolved relative to the package dir.
DEFAULT_PROMPT_TEMPLATE = Path(__file__).resolve().parent / "prompts" / "system.md"

# Ollama /api/generate timing/count fields, remapped to descriptive keys.
_TIMING_FIELDS: Dict[str, str] = {
    "load_duration": "load_duration_ns",
    "prompt_eval_count": "prompt_eval_count",
    "prompt_eval_duration": "prompt_eval_duration_ns",
    "eval_count": "eval_count",
    "eval_duration": "eval_duration_ns",
    "total_duration": "total_duration_ns",
}


class OllamaError(Exception):
    """Base class for all Ollama client errors."""


class OllamaConnectionError(OllamaError):
    """Ollama endpoint unreachable (e.g. connection refused)."""


class OllamaTimeoutError(OllamaError):
    """The request exceeded the configured timeout."""


class OllamaModelNotFoundError(OllamaError):
    """Ollama is running but the configured model is not pulled."""


class OllamaResponseError(OllamaError):
    """The response was malformed or had no usable response field."""


class OllamaTemplateError(OllamaError):
    """The prompt template path is missing or unreadable."""


@dataclass(frozen=True)
class OllamaResult:
    """Outcome of a single generate request."""

    ok: bool
    response: str
    latency_s: float
    ollama: Dict[str, object] = field(default_factory=dict)


class Transport(Protocol):
    """POSTs a JSON body and returns ``(status, raw_body)``.

    Implementations may raise ``urllib.error.URLError`` (connection refused)
    or ``socket.timeout``/``TimeoutError`` (timeout) to signal transport
    failures; ``OllamaClient`` maps those to typed errors.
    """

    def post(self, url: str, json_body: dict, timeout: float) -> Tuple[int, bytes]: ...


class UrllibTransport:
    """Stdlib ``urllib.request`` transport — the default HTTP implementation."""

    def post(self, url: str, json_body: dict, timeout: float) -> Tuple[int, bytes]:
        data = json.dumps(json_body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()


class TemplateLoader:
    """Reads the versioned system-role prompt template from disk."""

    def read(self, path: Path) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise OllamaTemplateError(f"cannot read prompt template {path}: {exc}") from exc


class OllamaClient:
    """HTTP client for a local Ollama API (``/api/generate``, stream:false)."""

    def __init__(
        self,
        endpoint: str,
        model: str,
        temperature: float,
        timeout: float,
        prompt_template: Path | str,
        transport: Optional[Transport] = None,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.prompt_template = Path(prompt_template)
        self._transport: Transport = transport or UrllibTransport()

    def probe(self) -> OllamaResult:
        """Run a connectivity probe: load the template and generate a reply."""
        system = TemplateLoader().read(self.prompt_template)
        return self.generate("Reply with 'ok' to confirm connectivity.", system=system)

    def generate(self, prompt: str, system: str) -> OllamaResult:
        """POST a non-streaming request and return the parsed result."""
        url = self.endpoint.rstrip("/") + "/api/generate"
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False,
        }

        start = time.monotonic()
        status, body = self._post(url, payload)
        latency = time.monotonic() - start

        if status != 200:
            self._raise_status_error(status, body)

        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise OllamaResponseError(f"invalid JSON from Ollama: {exc}") from exc

        response = data.get("response")
        if not isinstance(response, str) or not response:
            raise OllamaResponseError(
                "Ollama response missing a usable 'response' field"
            )

        ollama = {
            new_key: data[key] for key, new_key in _TIMING_FIELDS.items() if key in data
        }
        return OllamaResult(ok=True, response=response, latency_s=latency, ollama=ollama)

    def _post(self, url: str, payload: dict) -> Tuple[int, bytes]:
        try:
            return self._transport.post(url, payload, self.timeout)
        except OllamaError:
            raise
        except (socket.timeout, TimeoutError) as exc:
            raise OllamaTimeoutError(
                f"Ollama request timed out after {self.timeout}s"
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise OllamaConnectionError(
                f"cannot reach Ollama at {self.endpoint}: {exc}"
            ) from exc

    def _raise_status_error(self, status: int, body: bytes) -> None:
        message = ""
        try:
            message = str(json.loads(body.decode("utf-8")).get("error", ""))
        except (ValueError, UnicodeDecodeError, AttributeError):
            message = ""

        if "not found" in message.lower():
            raise OllamaModelNotFoundError(
                message or f"Ollama returned status {status}"
            )
        raise OllamaResponseError(
            message or f"Ollama returned unexpected status {status}"
        )
