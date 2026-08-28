"""Tests for the offline motion-graphics applier (Slice 2).

Covers ``MotionGraphicApplier.appraise``: a valid ``MotionGraphic`` becomes a
non-destructive ``InsertionDecision`` (kind ``intended_motion_graphic``), and
unknown template / bad param / out-of-range cases become typed rejections
(``template_rejected`` / ``param_rejected`` / ``range_rejected``). All assertions
exercise the real applier against a real ``TemplateLibrary`` and a real
``JsonlLogger`` — no timeline is ever mutated.
"""

from __future__ import annotations

import json
from pathlib import Path

from davinci_automation.jsonl_logger import JsonlLogger
from davinci_automation.llm_schema import MotionGraphic
from davinci_automation.motion_graphics import InsertionDecision, MotionGraphicApplier
from davinci_automation.template_library import TemplateLibrary
from davinci_automation.timecode import parse_timecode


def _mg(template: str, parametros: dict, timestamp: str = "00:00:06:00",
        duracion_frames: int = 48) -> MotionGraphic:
    return MotionGraphic(
        tipo="motion_graphic",
        timestamp=parse_timecode(timestamp),
        template=template,
        parametros=parametros,
        duracion_frames=duracion_frames,
    )


def _read_events(log_path: Path):
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]


# ---- spec: Valid action becomes a decision --------------------------------

def test_valid_motion_graphic_becomes_decision_logged_nothing_mutated(
    tmp_path: Path,
) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    decision = applier.appraise(
        _mg("lower_third", {"texto": "Hi", "duracion": 60}), duration=2880, logger=logger
    )

    assert decision.valid is True
    assert decision.kind == "intended_motion_graphic"
    assert decision.template_id == "lower_third"
    assert decision.timestamp == 144  # 00:00:06:00 at 24 fps
    assert decision.duration == 48
    # Merged param set: provided values + schema defaults for omitted params.
    assert decision.params["texto"] == "Hi"
    assert decision.params["duracion"] == 60
    assert decision.params["posicion"] == "bottom"
    assert decision.reason == ""

    events = _read_events(tmp_path / "run.jsonl")
    assert [e["event"] for e in events] == ["intended_motion_graphic"]
    assert events[0]["result"]["template_id"] == "lower_third"


def test_valid_decision_carries_resolved_template_by_display_name(
    tmp_path: Path,
) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    decision = applier.appraise(
        _mg("Title", {"texto": "Intro"}), duration=2880, logger=logger
    )

    assert decision.valid is True
    assert decision.template_id == "title"


# ---- spec: Param value validation ------------------------------------------

def test_param_type_mismatch_rejected_naming_param(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # lower_third's duracion is an int; passing a string must be rejected.
    decision = applier.appraise(
        _mg("lower_third", {"duracion": "sixty"}), duration=2880, logger=logger
    )

    assert decision.valid is False
    assert decision.kind == "param_rejected"
    assert "duracion" in decision.reason
    assert decision.template_id == "lower_third"

    events = _read_events(tmp_path / "run.jsonl")
    assert [e["event"] for e in events] == ["param_rejected"]
    assert events[0]["result"]["param"] == "duracion"


def test_param_out_of_bounds_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # lower_third's duracion max is 240; 9999 is out of bounds.
    decision = applier.appraise(
        _mg("lower_third", {"duracion": 9999}), duration=2880, logger=logger
    )

    assert decision.valid is False
    assert decision.kind == "param_rejected"
    assert "duracion" in decision.reason
    assert "above max" in decision.reason


def test_param_below_min_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # lower_third's duracion min is 1; 0 is below the floor.
    decision = applier.appraise(
        _mg("lower_third", {"duracion": 0}), duration=2880, logger=logger
    )

    assert decision.valid is False
    assert decision.kind == "param_rejected"
    assert "below min" in decision.reason


def test_unknown_param_name_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # "text" is not a lower_third param (it is "texto").
    decision = applier.appraise(
        _mg("lower_third", {"text": "Hi"}), duration=2880, logger=logger
    )

    assert decision.valid is False
    assert decision.kind == "param_rejected"
    assert "text" in decision.reason


# ---- triangulation: number-type param (callout) -----------------------------

def test_callout_number_param_validated(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # callout's duracion is a "number" param; an int is a valid number value.
    decision = applier.appraise(
        _mg("callout", {"texto": "Note", "duracion": 120}, timestamp="00:00:01:00"),
        duration=2880,
        logger=logger,
    )

    assert decision.valid is True
    assert decision.template_id == "callout"
    assert decision.params["duracion"] == 120
    assert decision.timestamp == 24  # 00:00:01:00 at 24 fps


def test_callout_number_out_of_bounds_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # callout's duracion max is 480; 5000 is out of bounds (number path).
    decision = applier.appraise(
        _mg("callout", {"texto": "Note", "duracion": 5000}), duration=2880, logger=logger
    )

    assert decision.valid is False
    assert decision.kind == "param_rejected"
    assert "above max" in decision.reason


# ---- spec: Range validation ------------------------------------------------

def test_out_of_range_timestamp_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    # 00:02:00:00 = frame 2880, equal to duration 2880 -> end exceeds range.
    decision = applier.appraise(
        _mg("lower_third", {"texto": "Hi"}, timestamp="00:02:00:00", duracion_frames=48),
        duration=2880,
        logger=logger,
    )

    assert decision.valid is False
    assert decision.kind == "range_rejected"
    assert decision.template_id == "lower_third"

    events = _read_events(tmp_path / "run.jsonl")
    assert [e["event"] for e in events] == ["range_rejected"]


def test_non_positive_duration_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    decision = applier.appraise(
        _mg("lower_third", {"texto": "Hi"}, duracion_frames=0),
        duration=2880,
        logger=logger,
    )

    assert decision.valid is False
    assert decision.kind == "range_rejected"


# ---- spec: Unknown template -------------------------------------------------

def test_unknown_template_rejected(tmp_path: Path) -> None:
    lib = TemplateLibrary.load()
    applier = MotionGraphicApplier(lib)
    logger = JsonlLogger(tmp_path / "run.jsonl")

    decision = applier.appraise(
        _mg("intro_banner", {"texto": "Hi"}), duration=2880, logger=logger
    )

    assert decision.valid is False
    assert decision.kind == "template_rejected"
    assert decision.template_id is None
    assert "intro_banner" in decision.reason

    events = _read_events(tmp_path / "run.jsonl")
    assert [e["event"] for e in events] == ["template_rejected"]
    assert events[0]["result"]["template"] == "intro_banner"