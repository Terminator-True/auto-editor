"""JSON-lines audit logger.

Writes one JSON object per line to a local file. Each record carries an event
name, a level, a timestamp, and an arbitrary result payload. The write path is
deliberately trivial (plain append) so logging never blocks the connect/read
flow (per spec).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonlLogger:
    """Append-only JSON-lines logger writing to ``path``."""

    def __init__(self, path: Path, level: str = "info") -> None:
        self.path = Path(path)
        self.level = level

    def write(self, event: str, level: str = "info", **result: Any) -> None:
        """Append one JSON object per line: ``{ts, event, level, result}``."""
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "level": level,
            "result": result,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")