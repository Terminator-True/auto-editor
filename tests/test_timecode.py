"""Tests for the ``Timecode`` value type and ``parse_timecode``."""

from __future__ import annotations

import pytest

from davinci_automation.timecode import FPS, Timecode, TimecodeError, parse_timecode


def test_fps_is_24() -> None:
    assert FPS == 24


def test_parse_valid_timecode() -> None:
    tc = parse_timecode("00:01:23:10")
    assert tc == Timecode(hour=0, minute=1, second=23, frame=10)
    assert (tc.hour, tc.minute, tc.second, tc.frame) == (0, 1, 23, 10)


def test_total_frames_is_hms_to_frames_plus_frame() -> None:
    tc = parse_timecode("00:01:23:10")
    # (0h + 1m + 23s) * 24fps + 10 frames = 83 * 24 + 10 = 2002
    assert tc.total_frames == ((0 * 3600 + 1 * 60 + 23) * FPS) + 10
    assert tc.total_frames == 2002


def test_parse_accepts_varying_hour_value() -> None:
    tc = parse_timecode("01:00:00:00")
    assert tc.total_frames == 3600 * FPS


def test_rejects_wrong_field_count() -> None:
    with pytest.raises(TimecodeError):
        parse_timecode("01:23:10")


def test_rejects_frame_out_of_range() -> None:
    with pytest.raises(TimecodeError) as exc_info:
        parse_timecode("00:01:23:99")
    assert "frame" in str(exc_info.value)
    assert "23" in str(exc_info.value)


def test_rejects_negative_frame() -> None:
    with pytest.raises(TimecodeError):
        parse_timecode("00:00:00:-1")


def test_rejects_minute_out_of_range() -> None:
    with pytest.raises(TimecodeError) as exc_info:
        parse_timecode("00:60:00:00")
    assert "minute" in str(exc_info.value)


def test_rejects_second_out_of_range() -> None:
    with pytest.raises(TimecodeError) as exc_info:
        parse_timecode("00:00:60:00")
    assert "second" in str(exc_info.value)