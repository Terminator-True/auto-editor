"""Tests for OllamaClient, TemplateLoader, and the CLI probe path.

Runs fully offline: success/error branches drive a fake transport, and an
end-to-end integration test uses a real stdlib ``http.server`` fake.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import URLError

import pytest

from davinci_automation.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTemplateError,
    OllamaTimeoutError,
    TemplateLoader,
    UrllibTransport,
)
from tests.fake_ollama import FakeTransport


# ---------------------------------------------------------------- TemplateLoader

def test_template_loader_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "system.md"
    path.write_text("# Version: 1\n\nBe concise.\n", encoding="utf-8")

    assert TemplateLoader().read(path) == "# Version: 1\n\nBe concise.\n"


def test_template_loader_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(OllamaTemplateError):
        TemplateLoader().read(tmp_path / "absent.md")


def test_template_loader_unreadable_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(OllamaTemplateError):
        TemplateLoader().read(tmp_path)


# ---------------------------------------------------------------- OllamaClient

def _client(transport, template: Path) -> OllamaClient:
    return OllamaClient(
        endpoint="http://localhost:11434",
        model="qwen2.5:14b",
        temperature=0.2,
        timeout=5.0,
        prompt_template=template,
        transport=transport,
    )


def test_generate_success_posts_stream_false_and_parses(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\nYou are a probe.\n", encoding="utf-8")
    transport = FakeTransport(
        status=200,
        body=json.dumps(
            {"response": "ok", "total_duration": 1500000000, "eval_count": 3}
        ).encode(),
    )
    client = _client(transport, template)

    result = client.generate("Hello", system="You are a probe.")

    assert result.ok is True
    assert result.response == "ok"
    assert result.latency_s >= 0
    assert result.ollama["total_duration_ns"] == 1500000000

    call = transport.calls[0]
    assert call["url"] == "http://localhost:11434/api/generate"
    assert call["json_body"]["model"] == "qwen2.5:14b"
    assert call["json_body"]["system"] == "You are a probe."
    assert call["json_body"]["prompt"] == "Hello"
    assert call["json_body"]["temperature"] == 0.2
    assert call["json_body"]["stream"] is False
    assert call["timeout"] == 5.0


def test_probe_loads_template_and_generates(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\nYou are a probe.\n", encoding="utf-8")
    transport = FakeTransport(status=200, body=b'{"response":"ok"}')
    client = _client(transport, template)

    result = client.probe()

    assert result.ok is True
    assert result.response == "ok"
    call = transport.calls[0]
    assert call["json_body"]["system"] == "# Version: 1\nYou are a probe.\n"


def test_probe_missing_template_raises(tmp_path: Path) -> None:
    transport = FakeTransport(status=200, body=b'{"response":"ok"}')
    client = _client(transport, tmp_path / "absent.md")

    with pytest.raises(OllamaTemplateError):
        client.probe()


def test_connection_refused_raises(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")
    transport = FakeTransport(error=URLError("connection refused"))
    client = _client(transport, template)

    with pytest.raises(OllamaConnectionError):
        client.probe()


def test_timeout_raises(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")
    transport = FakeTransport(error=socket.timeout("timed out"))
    client = _client(transport, template)

    with pytest.raises(OllamaTimeoutError):
        client.probe()


def test_model_not_found_raises(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")
    transport = FakeTransport(
        status=404, body=b'{"error":"model \\"qwen2.5:14b\\" not found"}'
    )
    client = _client(transport, template)

    with pytest.raises(OllamaModelNotFoundError):
        client.probe()


def test_malformed_json_raises(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")
    transport = FakeTransport(status=200, body=b"not json")
    client = _client(transport, template)

    with pytest.raises(OllamaResponseError):
        client.probe()


def test_missing_response_field_raises(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")
    transport = FakeTransport(status=200, body=b'{"total_duration":1}')
    client = _client(transport, template)

    with pytest.raises(OllamaResponseError):
        client.probe()


def test_non_200_with_garbage_body_raises_response_error(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")
    transport = FakeTransport(status=500, body=b"oops not json")
    client = _client(transport, template)

    with pytest.raises(OllamaResponseError):
        client.probe()


def test_transport_raising_typed_error_propagates(tmp_path: Path) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\n", encoding="utf-8")

    class _TypedTransport:
        def post(self, url, json_body, timeout):
            raise OllamaConnectionError("already typed")

    client = _client(_TypedTransport(), template)

    with pytest.raises(OllamaConnectionError):
        client.probe()


# ------------------------------------------------------------- http.server fake

@pytest.fixture
def fake_server():
    handler = _make_handler()
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


def test_integration_real_http_server(tmp_path: Path, fake_server: str) -> None:
    template = tmp_path / "system.md"
    template.write_text("# Version: 1\nYou are a probe.\n", encoding="utf-8")
    client = OllamaClient(
        endpoint=fake_server,
        model="qwen2.5:14b",
        temperature=0.2,
        timeout=5.0,
        prompt_template=template,
        transport=UrllibTransport(),
    )

    result = client.probe()

    assert result.ok is True
    assert result.response == "integration ok"
    assert result.latency_s >= 0
    assert result.ollama["total_duration_ns"] == 999


def _make_handler():
    canned = json.dumps(
        {"response": "integration ok", "total_duration": 999}
    ).encode()

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 (stdlib naming)
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(canned)))
            self.end_headers()
            self.wfile.write(canned)

        def log_message(self, *args):  # silence server logs
            pass

    return _Handler
