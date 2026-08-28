"""Tests for the JSON-lines audit logger."""

from __future__ import annotations

import json
from pathlib import Path

from davinci_automation.jsonl_logger import JsonlLogger


def _read_lines(path: Path) -> list:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_write_appends_one_valid_json_line(tmp_path: Path) -> None:
    log_path = tmp_path / "sub" / "run.jsonl"
    logger = JsonlLogger(log_path)

    logger.write("connection", "info", status="ok")

    lines = _read_lines(log_path)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "connection"
    assert record["level"] == "info"
    assert record["result"] == {"status": "ok"}
    assert "ts" in record


def test_write_appends_multiple_lines_in_order(tmp_path: Path) -> None:
    log_path = tmp_path / "run.jsonl"
    logger = JsonlLogger(log_path)

    logger.write("project", "info", name="P")
    logger.write("timeline", "info", name="T")

    records = [json.loads(line) for line in _read_lines(log_path)]
    assert [r["event"] for r in records] == ["project", "timeline"]


def test_write_creates_parent_directories(tmp_path: Path) -> None:
    log_path = tmp_path / "deep" / "nested" / "audit.jsonl"
    logger = JsonlLogger(log_path)
    logger.write("empty_timeline", "info")
    assert log_path.is_file()


def test_custom_level_and_payload(tmp_path: Path) -> None:
    log_path = tmp_path / "run.jsonl"
    JsonlLogger(log_path).write("connect_error", "error", message="boom")
    record = json.loads(_read_lines(log_path)[0])
    assert record["level"] == "error"
    assert record["result"] == {"message": "boom"}