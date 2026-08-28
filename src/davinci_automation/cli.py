"""CLI orchestration for the read-only Resolve connection slice.

``main()`` wires config -> logger -> connect -> read -> JSONL emission and maps
every failure mode to a non-zero exit code with a JSONL-logged error and no raw
traceback (per spec). Exit 0 on success including an empty timeline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from davinci_automation.config import ConfigError, load_config
from davinci_automation.jsonl_logger import JsonlLogger
from davinci_automation.ollama_client import OllamaClient, OllamaError
from davinci_automation.orchestrator import Orchestrator, OrchestratorError
from davinci_automation.reader import TimelineReader
from davinci_automation.resolve_client import (
    NoActiveTimeline,
    NoOpenProject,
    ResolveClient,
    ResolveNotRunning,
    ResolveScriptNotFound,
)
from davinci_automation.srt_reader import SrtError

DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_LOG_PATH = Path("logs/run.jsonl")


class _OllamaSeamAdapter:
    """Adapt ``OllamaClient.generate`` to the orchestrator's LLM seam.

    The orchestrator's LLM seam expects ``generate(prompt, system) -> str``
    (raw response text), but ``OllamaClient.generate`` returns an
    ``OllamaResult``. This adapter unwraps ``.response`` so the pipeline's
    ``parse_llm_output`` receives the raw text it expects.
    """

    def __init__(self, client) -> None:
        self._client = client

    def generate(self, prompt: str, system: str = "") -> str:
        return self._client.generate(prompt, system=system).response


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="davinci-automation",
        description="Connect to a running DaVinci Resolve and list active timeline clips.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file (default: %(default)s).",
    )
    parser.add_argument(
        "--probe-ollama",
        action="store_true",
        help="Run a connectivity probe against the local Ollama API and exit.",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run the end-to-end prototype flow (connect -> read -> transcribe -> LLM -> parse -> apply).",
    )
    parser.add_argument(
        "--mode",
        choices=["marker", "auto"],
        help="Operation mode for --e2e (default: config pipeline.mode, else marker).",
    )
    parser.add_argument(
        "--srt",
        default=None,
        help="Path to an .srt transcription for --e2e (overrides config transcription.srt_path).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logger: Optional[JsonlLogger] = None

    try:
        config = load_config(args.config)
        logger = JsonlLogger(config.log.path, config.log.level)

        if args.probe_ollama:
            return _probe_ollama(config, logger)

        if args.e2e:
            return _run_e2e(config, logger, args)

        client = ResolveClient(
            script_path=config.resolve.script_path,
            detect_version=config.resolve.detect_version,
        )

        client.connect()
        logger.write("connection", "info", status="ok")

        if config.resolve.detect_version:
            version = client.get_version()
            logger.write("version", "info", version=version or "unknown")

        project = client.active_project()
        logger.write("project", "info", name=project.GetName())

        timeline = client.active_timeline()
        logger.write("timeline", "info", name=timeline.GetName())

        result = TimelineReader().read(timeline, project_name=project.GetName())
        _emit_listing(logger, result)

        return 0

    except ConfigError as exc:
        _log_fallback_error(logger, "config_error", str(exc))
        return 1
    except ResolveScriptNotFound as exc:
        _log_fallback_error(logger, "script_not_found", str(exc))
        return 1
    except ResolveNotRunning as exc:
        _log_fallback_error(logger, "connect_error", str(exc))
        return 1
    except NoOpenProject as exc:
        _log_fallback_error(logger, "project_error", str(exc))
        return 1
    except NoActiveTimeline as exc:
        _log_fallback_error(logger, "timeline_error", str(exc))
        return 1
    except OllamaError as exc:
        _log_fallback_error(logger, "probe_error", str(exc))
        return 1
    except (SrtError, OrchestratorError) as exc:
        _log_fallback_error(logger, "error", str(exc))
        return 1


def _run_e2e(config, logger: JsonlLogger, args) -> int:
    """Run the end-to-end prototype: config -> logger -> Orchestrator.

    Resolves the operation mode (``--mode`` overrides ``config.pipeline.mode``)
    and the SRT source (``--srt`` overrides ``config.transcription.srt_path``),
    then composes the real ``ResolveClient`` with an Ollama transport adapted to
    the orchestrator's raw-text LLM seam. The orchestrator logs every stage and
    maps each failure mode to a JSONL ``error`` + return 1 (no raw traceback).
    """
    mode = args.mode or config.pipeline.mode

    srt_path = Path(args.srt) if args.srt else config.transcription.srt_path
    if srt_path is None:
        raise SrtError("no SRT source: pass --srt or set transcription.srt_path")
    try:
        srt_text = srt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SrtError(f"cannot read SRT {srt_path}: {exc}") from exc

    client = ResolveClient(
        script_path=config.resolve.script_path,
        detect_version=config.resolve.detect_version,
    )
    ollama = OllamaClient(
        endpoint=config.ollama.endpoint,
        model=config.ollama.model,
        temperature=config.ollama.temperature,
        timeout=config.ollama.timeout,
        prompt_template=config.ollama.prompt_template,
    )

    orchestrator = Orchestrator(
        resolve_client=client,
        transport=_OllamaSeamAdapter(ollama),
        srt_source=lambda: srt_text,
        mode=mode,
    )
    return orchestrator.run(logger)


def _probe_ollama(config, logger: JsonlLogger) -> int:
    """Run a single non-streaming Ollama probe and log latency + timing."""
    client = OllamaClient(
        endpoint=config.ollama.endpoint,
        model=config.ollama.model,
        temperature=config.ollama.temperature,
        timeout=config.ollama.timeout,
        prompt_template=config.ollama.prompt_template,
    )

    logger.write(
        "probe_start",
        "info",
        endpoint=config.ollama.endpoint,
        model=config.ollama.model,
    )
    result = client.probe()
    logger.write(
        "probe_success",
        "info",
        response=result.response,
        latency_s=result.latency_s,
        **result.ollama,
    )
    return 0


def _emit_listing(logger: JsonlLogger, result) -> None:
    """Emit track/clip JSONL records, or an empty-timeline event."""
    has_clips = any(track.clips for track in result.tracks)

    if not has_clips:
        logger.write(
            "empty_timeline",
            "info",
            project=result.project,
            timeline=result.timeline,
            tracks=len(result.tracks),
        )
        return

    for track in result.tracks:
        logger.write("track", "info", index=track.index, kind=track.kind)
        for clip in track.clips:
            logger.write(
                "clip",
                "info",
                track=track.index,
                name=clip.name,
                start=clip.start,
                end=clip.end,
            )


def _log_fallback_error(logger: Optional[JsonlLogger], event: str, message: str) -> None:
    """Log an error to the configured logger, or a fallback when config failed."""
    target = logger or JsonlLogger(DEFAULT_LOG_PATH)
    target.write(event, "error", message=message)


if __name__ == "__main__":
    sys.exit(main())