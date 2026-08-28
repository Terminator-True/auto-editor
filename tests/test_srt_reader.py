"""Offline unit tests for the Slice 2 SRT reader.

Covers the ``transcription-srt`` spec: typical multi-cue parsing, multi-line
and unnumbered cues, empty input, and malformed timestamps. All cases run
against static strings — no live services.
"""

from __future__ import annotations

import pytest

from davinci_automation.srt_reader import SrtCue, SrtError, parse_srt


def test_parse_typical_multi_cue_srt() -> None:
    srt = (
        "1\n"
        "00:00:01,000 --> 00:00:03,500\n"
        "Hello and welcome.\n"
        "\n"
        "2\n"
        "00:00:05,000 --> 00:00:08,000\n"
        "This is a test timeline.\n"
    )

    cues = parse_srt(srt)

    assert len(cues) == 2
    first, second = cues
    assert first.index == 1
    assert first.start == 1.0
    assert first.end == 3.5
    assert first.text == "Hello and welcome."
    assert second.index == 2
    assert second.start == 5.0
    assert second.end == 8.0
    assert second.text == "This is a test timeline."


def test_parse_multiline_text_preserves_full_text() -> None:
    srt = (
        "1\n"
        "00:00:01,000 --> 00:00:04,000\n"
        "First line\n"
        "Second line\n"
    )

    cues = parse_srt(srt)

    assert len(cues) == 1
    assert cues[0].text == "First line\nSecond line"


def test_parse_unnumbered_cues_uses_none_index() -> None:
    srt = (
        "00:00:02,000 --> 00:00:03,000\n"
        "No index here.\n"
        "\n"
        "00:00:05,000 --> 00:00:06,000\n"
        "Still fine.\n"
    )

    cues = parse_srt(srt)

    assert len(cues) == 2
    assert cues[0].index is None
    assert cues[1].index is None
    assert cues[0].start == 2.0
    assert cues[1].text == "Still fine."


def test_parse_accepts_dot_millisecond_separator() -> None:
    srt = "00:00:01,500 --> 00:00:02,750\nDot and comma tolerated.\n"

    cues = parse_srt(srt)

    assert len(cues) == 1
    assert cues[0].start == 1.5
    assert cues[0].end == 2.75


def test_parse_empty_text_raises_srt_error() -> None:
    with pytest.raises(SrtError):
        parse_srt("")


def test_parse_whitespace_only_raises_srt_error() -> None:
    with pytest.raises(SrtError):
        parse_srt("   \n  \n")


def test_parse_malformed_timecode_raises_srt_error() -> None:
    srt = "1\nnot-a-timecode\nSome text.\n"
    with pytest.raises(SrtError):
        parse_srt(srt)


def test_parse_cue_missing_timecode_line_raises_srt_error() -> None:
    # An index line with no timecode after it is structurally malformed.
    srt = "1\n\n2\n00:00:01,000 --> 00:00:02,000\nA cue.\n"
    with pytest.raises(SrtError):
        parse_srt(srt)


def test_parse_tolerates_blank_line_runs_between_cues() -> None:
    srt = (
        "1\n"
        "00:00:01,000 --> 00:00:02,000\n"
        "First.\n"
        "\n"
        "\n"
        "\n"
        "2\n"
        "00:00:05,000 --> 00:00:06,000\n"
        "Second.\n"
    )

    cues = parse_srt(srt)

    assert len(cues) == 2
    assert cues[0].text == "First."
    assert cues[1].text == "Second."


def test_parse_cue_start_and_end_converted_to_seconds() -> None:
    srt = "1\n01:00:00,000 --> 01:00:30,000\nLong caption.\n"

    cues = parse_srt(srt)

    assert cues[0].start == 3600.0
    assert cues[0].end == 3630.0