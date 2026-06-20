import os
import json
import tempfile
from pathlib import Path
from typing import Optional


def _base_dir() -> Path:
    # Allow tests to override via env var
    return Path(os.environ.get("EVENT_REGISTRY_BASE", "event_registry"))


def _registry_path() -> Path:
    base = _base_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / "registry.json"


def load_registry() -> dict:
    p = _registry_path()
    if not p.exists():
        return {"events": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Corrupt file -> return empty structure
        return {"events": []}


def save_registry(data: dict):
    p = _registry_path()
    # atomic write
    dirp = p.parent
    # tempfile.mkstemp historically accepts a string path for dir; ensure we
    # pass a str to avoid TypeError on some Python/OS combinations when dir
    # is a pathlib.Path (observed on some Windows setups).
    fd, tmp = tempfile.mkstemp(dir=str(dirp))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def _find_event(data: dict, event_id: str) -> Optional[dict]:
    for e in data.get("events", []):
        if e.get("event_id") == event_id:
            return e
    return None


def add_event(event_entry: dict):
    data = load_registry()
    if _find_event(data, event_entry.get("event_id")):
        # already exists, no-op
        return
    data.setdefault("events", []).append(event_entry)
    save_registry(data)


def append_timestamp_to_event(event_id: str, timestamp: float, confidence: Optional[float] = None):
    data = load_registry()
    ev = _find_event(data, event_id)
    if not ev:
        raise KeyError(f"event {event_id} not found")
    ev.setdefault("timestamps", [])
    if timestamp not in ev["timestamps"]:
        ev["timestamps"].append(timestamp)
    if confidence is not None:
        ev.setdefault("confidence_history", []).append(confidence)
    save_registry(data)
