import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import requests
import pytest

from src.analysis.ollama_client import OllamaClient
from src.analysis.moondream_classifier import MoondreamClassifier
from src.storage.metadata_store import FileMetadataStore


class MockOllamaHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('content-length', '0'))
        b = self.rfile.read(length)
        payload = json.loads(b)
        # respond with fixed labels
        resp = {"results": [{"label": "cat", "confidence": 0.8}, {"label": "animal", "confidence": 0.5}]}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode('utf-8'))


@pytest.fixture(scope='module')
def mock_server():
    server = HTTPServer(('localhost', 11435), MockOllamaHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield server
    server.shutdown()


def test_e2e_classify_and_persist(tmp_path, mock_server):
    # point client to mock server port
    client = OllamaClient(base_url='http://localhost:11435', timeout_ms=2000, retries=1)
    store = FileMetadataStore(base_path=str(tmp_path))
    classifier = MoondreamClassifier(client, store)

    frame = {"frame_id": "frame123", "data": "binary-or-encoded"}
    res = classifier.classify_frame(frame)

    assert res['frame_id'] == 'frame123'
    assert res['top_label'] in ('cat', 'animal')
    # persisted file exists
    loaded = store.load_metadata('frame123')
    assert loaded['frame_id'] == 'frame123'
    assert 'accuracy' in loaded
