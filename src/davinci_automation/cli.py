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
from davinci_automation.reader import TimelineReader
from davinci_automation.resolve_client import (
    NoActiveTimeline,
    NoOpenProject,
    ResolveClient,
    ResolveNotRunning,
    ResolveScriptNotFound,
)

DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_LOG_PATH = Path("logs/run.jsonl")


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
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logger: Optional[JsonlLogger] = None

    try:
        config = load_config(args.config)
        logger = JsonlLogger(config.log.path, config.log.level)

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