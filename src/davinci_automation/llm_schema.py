"""Strict offline validator for the frozen LLM output contract (§4).

``parse_llm_output`` turns raw LLM text into typed dataclasses or raises a
typed error mirroring the repo's ``OllamaError``-base hierarchy. It validates
against the versioned schema document shipped as package data
(``schemas/llm_output.v1.json``) with no coercion and no live services.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Dict, Optional, Tuple

import jsonschema

from davinci_automation.timecode import (
    Timecode,
    TimecodeError as _TimecodeError,
    parse_timecode,
)


class LlmOutputError(Exception):
    """Base class for all LLM output parse/validation errors."""


class JsonParseError(LlmOutputError):
    """The raw LLM text was not parseable JSON."""


class SchemaValidationError(LlmOutputError):
    """The JSON parsed but did not match the frozen schema."""

    def __init__(self, message: str, path: Tuple = (), expected: str = "") -> None:
        self.path = tuple(path)
        self.expected = expected
        super().__init__(message)


class TimecodeError(_TimecodeError, LlmOutputError):
    """A timecode string was invalid; also an ``LlmOutputError``."""


@dataclass(frozen=True)
class Segmento:
    inicio: Timecode
    fin: Timecode


@dataclass(frozen=True)
class Corte:
    tipo: str
    rango: Segmento
    motivo: str


@dataclass(frozen=True)
class MotionGraphic:
    tipo: str
    timestamp: Timecode
    template: str
    parametros: Dict[str, Any]
    duracion_frames: int


@dataclass(frozen=True)
class LlmOutput:
    segmento: Segmento
    acciones: list


# Per-action-type allowed field sets, used only to build precise error messages.
_CORTE_FIELDS = {"tipo", "rango", "motivo"}
_MOTION_GRAPHIC_FIELDS = {"tipo", "timestamp", "template", "parametros", "duracion_frames"}


def _load_schema() -> Dict[str, Any]:
    resource = files("davinci_automation").joinpath("schemas/llm_output.v1.json")
    with resource.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_SCHEMA: Dict[str, Any] = _load_schema()


def _diagnose(data: Any) -> Optional[Tuple[str, Tuple, str]]:
    """Return a precise ``(message, path, expected)`` for the first problem.

    ``jsonschema`` collapses ``oneOf`` failures to a single opaque ``const``
    error that neither names an unexpected field nor the unsupported ``tipo``
    value. This pass runs only when structural validation already failed, to
    turn that into an actionable §3.2 retry message. Returns ``None`` when no
    targeted problem is found (caller falls back to jsonschema's message).
    """
    if not isinstance(data, dict):
        return "schema invalid; root must be an object", (), "an object"

    segmento = data.get("segmento")
    if not isinstance(segmento, dict):
        return "schema invalid; 'segmento' must be an object", ("segmento",), "an object"
    for field in ("inicio", "fin"):
        if field not in segmento:
            return (
                f"schema invalid; 'segmento' is missing required field '{field}'",
                ("segmento",),
                f"'{field}' required",
            )

    acciones = data.get("acciones")
    if not isinstance(acciones, list):
        return "schema invalid; 'acciones' must be an array", ("acciones",), "an array"

    for index, action in enumerate(acciones):
        path = ("acciones", index)
        if not isinstance(action, dict):
            return (
                f"schema invalid; 'acciones[{index}]' must be an object",
                path,
                "an object",
            )

        tipo = action.get("tipo")
        if tipo == "corte":
            allowed = _CORTE_FIELDS
        elif tipo == "motion_graphic":
            allowed = _MOTION_GRAPHIC_FIELDS
        else:
            return (
                f"schema invalid; 'acciones[{index}].tipo' has unsupported value {tipo!r}",
                path + ("tipo",),
                "one of 'corte', 'motion_graphic'",
            )

        unknown = [key for key in action if key not in allowed]
        if unknown:
            return (
                f"schema invalid; 'acciones[{index}]' has unexpected field(s) "
                f"{', '.join(sorted(unknown))}",
                path,
                "no additional fields",
            )

        if tipo == "corte":
            rango = action.get("rango")
            if not isinstance(rango, dict):
                return (
                    f"schema invalid; 'acciones[{index}].rango' must be an object",
                    path + ("rango",),
                    "an object",
                )
            for field in ("inicio", "fin"):
                if field not in rango:
                    return (
                        f"schema invalid; 'acciones[{index}].rango' is missing "
                        f"required field '{field}'",
                        path + ("rango",),
                        f"'{field}' required",
                    )
        else:
            for field in ("timestamp", "template", "parametros", "duracion_frames"):
                if field not in action:
                    return (
                        f"schema invalid; 'acciones[{index}]' is missing required "
                        f"field '{field}'",
                        path,
                        f"'{field}' required",
                    )
            duracion = action.get("duracion_frames")
            if isinstance(duracion, bool) or not isinstance(duracion, int) or duracion < 0:
                return (
                    f"schema invalid; 'acciones[{index}].duracion_frames' must be a "
                    "non-negative integer",
                    path + ("duracion_frames",),
                    "non-negative integer",
                )

    return None


def _schema_error(error: jsonschema.ValidationError, data: Any) -> Tuple[str, Tuple, str]:
    diag = _diagnose(data)
    if diag is not None:
        return diag
    location = "/".join(str(part) for part in error.path) or "root"
    message = f"schema invalid at {location}: {error.message}"
    return message, tuple(error.path), error.message


def _parse_timecode(value: str, field: str) -> Timecode:
    try:
        return parse_timecode(value)
    except _TimecodeError as exc:
        raise TimecodeError(f"{field}: {exc}") from exc


def _build_segmento(data: Dict[str, Any]) -> Segmento:
    return Segmento(
        inicio=_parse_timecode(data["inicio"], "segmento.inicio"),
        fin=_parse_timecode(data["fin"], "segmento.fin"),
    )


def _build_action(data: Dict[str, Any]) -> Corte | MotionGraphic:
    if data["tipo"] == "corte":
        return Corte(
            tipo=data["tipo"],
            rango=Segmento(
                inicio=_parse_timecode(data["rango"]["inicio"], "acciones[].rango.inicio"),
                fin=_parse_timecode(data["rango"]["fin"], "acciones[].rango.fin"),
            ),
            motivo=data["motivo"],
        )
    return MotionGraphic(
        tipo=data["tipo"],
        timestamp=_parse_timecode(data["timestamp"], "acciones[].timestamp"),
        template=data["template"],
        parametros=data["parametros"],
        duracion_frames=data["duracion_frames"],
    )


def parse_llm_output(text: str) -> LlmOutput:
    """Parse raw LLM text into a typed ``LlmOutput``.

    Raises ``JsonParseError`` for malformed JSON, ``SchemaValidationError``
    for structural violations, and ``TimecodeError`` for bad timecodes. No
    values are coerced; empty ``acciones`` is valid.
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise JsonParseError(f"invalid JSON from LLM: {exc}") from exc

    try:
        jsonschema.validate(instance=data, schema=_SCHEMA)
    except jsonschema.ValidationError as exc:
        message, path, expected = _schema_error(exc, data)
        raise SchemaValidationError(message, path=path, expected=expected) from exc

    return LlmOutput(
        segmento=_build_segmento(data["segmento"]),
        acciones=[_build_action(action) for action in data["acciones"]],
    )