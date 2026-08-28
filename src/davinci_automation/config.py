"""Externalized configuration loading and validation.

Loads a YAML config file into typed dataclasses. The orchestrator reads all
runtime values from here — no hardcoded runtime literals (per spec).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from davinci_automation.ollama_client import DEFAULT_PROMPT_TEMPLATE


class ConfigError(Exception):
    """Raised when the config file is missing, invalid, or malformed."""


@dataclass(frozen=True)
class ResolveConfig:
    """Resolve connection settings."""

    script_path: Optional[str] = None
    detect_version: bool = True


@dataclass(frozen=True)
class LogConfig:
    """Audit logging settings."""

    path: Path = Path("logs/run.jsonl")
    level: str = "info"


@dataclass(frozen=True)
class OllamaConfig:
    """Local Ollama API connection settings."""

    endpoint: str = "http://localhost:11434"
    model: str = "qwen2.5:14b"
    temperature: float = 0.2
    timeout: float = 120.0
    prompt_template: Path = DEFAULT_PROMPT_TEMPLATE


@dataclass(frozen=True)
class PipelineConfig:
    """E2E pipeline operation settings."""

    mode: str = "marker"


@dataclass(frozen=True)
class TranscriptionConfig:
    """Transcription source settings for the E2E flow."""

    srt_path: Optional[Path] = None


@dataclass(frozen=True)
class Config:
    """Top-level validated configuration."""

    resolve: ResolveConfig = field(default_factory=ResolveConfig)
    log: LogConfig = field(default_factory=LogConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Build a Config from a parsed YAML mapping, validating each field."""
        if not isinstance(data, dict):
            raise ConfigError("config root must be a mapping")

        resolve_data = data.get("resolve", {})
        log_data = data.get("log", {})
        ollama_data = data.get("ollama", {})
        pipeline_data = data.get("pipeline", {})
        transcription_data = data.get("transcription", {})
        if not isinstance(resolve_data, dict) or not isinstance(log_data, dict):
            raise ConfigError("'resolve' and 'log' sections must be mappings")
        if not isinstance(ollama_data, dict):
            raise ConfigError("'ollama' section must be a mapping")
        if not isinstance(pipeline_data, dict):
            raise ConfigError("'pipeline' section must be a mapping")
        if not isinstance(transcription_data, dict):
            raise ConfigError("'transcription' section must be a mapping")

        return cls(
            resolve=_parse_resolve(resolve_data),
            log=_parse_log(log_data),
            ollama=_parse_ollama(ollama_data),
            pipeline=_parse_pipeline(pipeline_data),
            transcription=_parse_transcription(transcription_data),
        )


def _parse_resolve(data: Dict[str, Any]) -> ResolveConfig:
    script_path = data.get("script_path")
    if script_path is not None and not isinstance(script_path, str):
        raise ConfigError("'resolve.script_path' must be a string or null")

    detect_version = data.get("detect_version", True)
    if not isinstance(detect_version, bool):
        raise ConfigError("'resolve.detect_version' must be a boolean")

    return ResolveConfig(script_path=script_path, detect_version=detect_version)


def _parse_log(data: Dict[str, Any]) -> LogConfig:
    path = data.get("path", "logs/run.jsonl")
    if not isinstance(path, str) or not path:
        raise ConfigError("'log.path' must be a non-empty string")

    level = data.get("level", "info")
    if not isinstance(level, str) or not level:
        raise ConfigError("'log.level' must be a non-empty string")

    return LogConfig(path=Path(path), level=level)


def _parse_ollama(data: Dict[str, Any]) -> OllamaConfig:
    endpoint = data.get("endpoint", "http://localhost:11434")
    if not isinstance(endpoint, str) or not endpoint:
        raise ConfigError("'ollama.endpoint' must be a non-empty string")

    model = data.get("model", "qwen2.5:14b")
    if not isinstance(model, str) or not model:
        raise ConfigError("'ollama.model' must be a non-empty string")

    temperature = data.get("temperature", 0.2)
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ConfigError("'ollama.temperature' must be a number")

    timeout = data.get("timeout", 120.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ConfigError("'ollama.timeout' must be a number")

    prompt_template = data.get("prompt_template", str(DEFAULT_PROMPT_TEMPLATE))
    if not isinstance(prompt_template, str) or not prompt_template:
        raise ConfigError("'ollama.prompt_template' must be a non-empty string")

    return OllamaConfig(
        endpoint=endpoint,
        model=model,
        temperature=float(temperature),
        timeout=float(timeout),
        prompt_template=Path(prompt_template),
    )


def _parse_pipeline(data: Dict[str, Any]) -> PipelineConfig:
    mode = data.get("mode", "marker")
    if not isinstance(mode, str) or mode not in ("marker", "auto"):
        raise ConfigError("'pipeline.mode' must be 'marker' or 'auto'")
    return PipelineConfig(mode=mode)


def _parse_transcription(data: Dict[str, Any]) -> TranscriptionConfig:
    srt_path = data.get("srt_path")
    if srt_path is not None and not isinstance(srt_path, str):
        raise ConfigError("'transcription.srt_path' must be a string or null")
    return TranscriptionConfig(srt_path=Path(srt_path) if srt_path else None)


def load_config(path: Path | str) -> Config:
    """Load and validate a YAML config file.

    Raises ``ConfigError`` when the file is missing, unparsable, or invalid.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {config_path}: {exc}") from exc

    if data is None:
        raise ConfigError(f"config file is empty: {config_path}")

    return Config.from_dict(data)