"""End-to-end orchestration skeleton (Slice 1).

Composes the shipped foundations — ``ResolveClient``/``TimelineReader``, an
injectable LLM transport, and ``parse_llm_output`` — into one offline-testable
pipeline: connect -> read timeline -> transcribe -> LLM -> parse -> range
validate -> apply. Every stage is audited as a JSONL event via ``JsonlLogger``.

Slice 2 replaces the Slice 1 inline SRT helper with ``srt_reader.parse_srt``
(parse-only; chunking is intentionally deferred). Marker application is inline
here and moves to ``apply.py`` in Slice 3. Marker mode is the default and is
non-destructive (markers only); ``auto`` mode logs intended cuts and never
mutates the timeline.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from davinci_automation.jsonl_logger import JsonlLogger
from davinci_automation.srt_reader import SrtError, parse_srt
from davinci_automation.llm_schema import LlmOutputError, parse_llm_output
from davinci_automation.ollama_client import (
    DEFAULT_PROMPT_TEMPLATE,
    OllamaError,
    TemplateLoader,
)
from davinci_automation.reader import TimelineReader

DEFAULT_MODE = "marker"

_SYSTEM_PROMPT = TemplateLoader().read(DEFAULT_PROMPT_TEMPLATE)


class OrchestratorError(Exception):
    """Base error for orchestration-stage failures."""


class TranscriptionError(OrchestratorError):
    """Raised when the transcription source is empty or has no usable cues."""


def validate_range(start: int, end: int, duration: int) -> bool:
    """True when ``[start, end)`` is a valid cut range within ``duration``.

    Rejects negative starts, empty/inverted ranges (``start >= end``), and
    ranges that extend past the timeline end (§3.3).
    """
    return start >= 0 and start < end and end <= duration


class Orchestrator:
    """Compose the E2E pipeline behind injectable seams for offline testing."""

    def __init__(
        self,
        resolve_client,
        transport,
        srt_source: Callable[[], str],
        timeline_duration: Optional[Callable[[object], int]] = None,
        mode: str = DEFAULT_MODE,
        library=None,
        applier=None,
    ) -> None:
        # Imported lazily to avoid a circular import: motion_graphics reuses
        # validate_range from this module at module load time.
        from davinci_automation.motion_graphics import MotionGraphicApplier
        from davinci_automation.template_library import TemplateLibrary

        if library is None:
            library = TemplateLibrary.load()
        if applier is None:
            applier = MotionGraphicApplier(library)

        self.resolve_client = resolve_client
        self.transport = transport  # LLM seam: generate(prompt, system) -> raw text
        self.srt_source = srt_source
        self.timeline_duration = timeline_duration or (
            lambda timeline: timeline.GetEndFrame()
        )
        self.mode = mode
        self.library = library
        self.applier = applier

    def run(self, logger: JsonlLogger) -> int:
        """Run the pipeline; return 0 on success, 1 on any logged stage error."""
        try:
            self._connect(logger)
            timeline = self._read(logger)
            duration = self.timeline_duration(timeline)
            prompt = self._transcribe(logger)
            raw = self._generate(logger, prompt)
            output = self._parse(logger, raw)
            valid = self._validate(logger, output, duration)
            self._apply(logger, timeline, valid)
            return 0
        except (OllamaError, LlmOutputError, OrchestratorError, SrtError) as exc:
            logger.write("error", "error", message=str(exc))
            return 1

    # -- stages -------------------------------------------------------------

    def _connect(self, logger: JsonlLogger) -> None:
        self.resolve_client.connect()
        logger.write("connection", "info", status="ok")

    def _read(self, logger: JsonlLogger):
        project = self.resolve_client.active_project()
        timeline = self.resolve_client.active_timeline()
        result = TimelineReader().read(timeline, project.GetName())
        logger.write(
            "timeline",
            "info",
            project=result.project,
            timeline=result.timeline,
            tracks=len(result.tracks),
        )
        return timeline

    def _transcribe(self, logger: JsonlLogger) -> str:
        cues = parse_srt(self.srt_source())
        usable = [cue.text for cue in cues if cue.text.strip()]
        if not usable:
            raise TranscriptionError("SRT transcription has no usable cues")
        logger.write("transcription", "info", cues=len(usable))
        return " ".join(usable)

    def _generate(self, logger: JsonlLogger, prompt: str) -> str:
        raw = self.transport.generate(prompt, system=_SYSTEM_PROMPT)
        logger.write("llm", "info", characters=len(raw))
        return raw

    def _parse(self, logger: JsonlLogger, raw: str):
        output = parse_llm_output(raw)
        logger.write("parse", "info", acciones=len(output.acciones))
        return output

    def _validate(self, logger: JsonlLogger, output, duration: int) -> List:
        valid = []
        for action in output.acciones:
            if action.tipo == "motion_graphic":
                # Non-destructive: the applier logs the decision/rejection and
                # never mutates the timeline; it is not added to the corte list.
                self.applier.appraise(action, duration, logger)
                continue
            if action.tipo != "corte":
                continue
            start = action.rango.inicio.total_frames
            end = action.rango.fin.total_frames
            if validate_range(start, end, duration):
                valid.append(action)
            else:
                logger.write(
                    "range_rejected",
                    "error",
                    start=start,
                    end=end,
                    duration=duration,
                )
        logger.write(
            "validate", "info", accepted=len(valid), total=len(output.acciones)
        )
        return valid

    def _apply(self, logger: JsonlLogger, timeline, valid: List) -> None:
        if self.mode == "auto":
            for corte in valid:
                logger.write(
                    "intended_cut",
                    "info",
                    start=corte.rango.inicio.total_frames,
                    end=corte.rango.fin.total_frames,
                )
            return

        for corte in valid:
            frame = corte.rango.inicio.total_frames
            timeline.AddMarker(frame)
            logger.write("apply", "info", frame=frame)