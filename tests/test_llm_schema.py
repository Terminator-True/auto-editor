"""Tests for ``parse_llm_output`` and the frozen v1 schema."""

from __future__ import annotations

import json
from importlib.resources import files

import pytest

from davinci_automation.llm_schema import (
    Corte,
    JsonParseError,
    LlmOutput,
    MotionGraphic,
    SchemaValidationError,
    TimecodeError,
    parse_llm_output,
)
from davinci_automation.timecode import Timecode

# The exact §4 example from requisitos-proyecto-davinci-automation.md.
VALID_OUTPUT = """{
  "segmento": { "inicio": "00:01:23:10", "fin": "00:01:45:02" },
  "acciones": [
    {
      "tipo": "corte",
      "rango": { "inicio": "00:01:25:00", "fin": "00:01:28:15" },
      "motivo": "silencio/muletilla"
    },
    {
      "tipo": "motion_graphic",
      "timestamp": "00:01:30:00",
      "template": "lower_third_nombre",
      "parametros": { "texto_principal": "...", "texto_secundario": "..." },
      "duracion_frames": 90
    }
  ]
}"""


def _payload(segmento: str, acciones: str) -> str:
    return '{"segmento": ' + segmento + ', "acciones": ' + acciones + "}"


def _segmento(inicio: str = "00:01:00:00", fin: str = "00:01:05:00") -> str:
    return f'{{"inicio": "{inicio}", "fin": "{fin}"}}'


def test_schema_doc_loads_from_package() -> None:
    resource = files("davinci_automation").joinpath("schemas/llm_output.v1.json")
    doc = json.loads(resource.read_text(encoding="utf-8"))
    assert doc["properties"]["acciones"]["type"] == "array"
    assert doc["properties"]["segmento"]["required"] == ["inicio", "fin"]
    assert doc["definitions"]["motion_graphic"]["properties"]["duracion_frames"][
        "minimum"
    ] == 0


def test_accepts_exact_spec_example() -> None:
    out = parse_llm_output(VALID_OUTPUT)
    assert isinstance(out, LlmOutput)
    assert out.segmento.inicio == Timecode(0, 1, 23, 10)
    assert out.segmento.fin == Timecode(0, 1, 45, 2)
    assert len(out.acciones) == 2

    corte = out.acciones[0]
    assert isinstance(corte, Corte)
    assert corte.tipo == "corte"
    assert corte.motivo == "silencio/muletilla"
    assert corte.rango.inicio == Timecode(0, 1, 25, 0)
    assert corte.rango.fin == Timecode(0, 1, 28, 15)

    mg = out.acciones[1]
    assert isinstance(mg, MotionGraphic)
    assert mg.tipo == "motion_graphic"
    assert mg.timestamp == Timecode(0, 1, 30, 0)
    assert mg.template == "lower_third_nombre"
    assert mg.parametros == {"texto_principal": "...", "texto_secundario": "..."}
    assert mg.duracion_frames == 90


def test_empty_acciones_is_valid_and_meaningful() -> None:
    out = parse_llm_output(_payload(_segmento(), "[]"))
    assert out.acciones == []
    assert out.segmento.inicio == Timecode(0, 1, 0, 0)


def test_malformed_json_raises() -> None:
    with pytest.raises(JsonParseError):
        parse_llm_output('{"segmento": {inicio: "00:01:00:00"}}')


def test_trailing_comma_json_raises() -> None:
    with pytest.raises(JsonParseError):
        parse_llm_output('{"segmento": {},}')


def test_missing_fin_raises_schema_error_naming_path() -> None:
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload('{"inicio": "00:01:00:00"}', "[]"))
    message = str(exc_info.value)
    assert "fin" in message
    assert "segmento" in message
    assert exc_info.value.path == ("segmento",)
    assert exc_info.value.expected


def test_acciones_not_array_raises() -> None:
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(
            _payload(_segmento(), '{"tipo": "corte"}')
        )
    assert "acciones" in str(exc_info.value)


def test_unknown_tipo_raises_naming_value() -> None:
    accion = (
        '{"tipo": "fade", "rango": {"inicio": "00:01:00:00", "fin": "00:01:01:00"},'
        ' "motivo": "x"}'
    )
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))
    assert "fade" in str(exc_info.value)


def test_extra_unknown_key_raises_naming_field() -> None:
    accion = (
        '{"tipo": "corte", "rango": {"inicio": "00:01:00:00", "fin": "00:01:01:00"},'
        ' "motivo": "x", "extra": 1}'
    )
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))
    assert "extra" in str(exc_info.value)


def test_negative_duracion_frames_raises() -> None:
    accion = (
        '{"tipo": "motion_graphic", "timestamp": "00:01:00:00", "template": "t",'
        ' "parametros": {}, "duracion_frames": -5}'
    )
    with pytest.raises(SchemaValidationError):
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))


def test_invalid_timecode_in_payload_raises_timecode_error() -> None:
    with pytest.raises(TimecodeError):
        parse_llm_output(_payload(_segmento(inicio="00:01:00:99"), "[]"))


def test_root_not_object_raises() -> None:
    with pytest.raises(SchemaValidationError):
        parse_llm_output("[1, 2, 3]")


def test_segmento_not_object_raises() -> None:
    with pytest.raises(SchemaValidationError):
        parse_llm_output('{"segmento": 5, "acciones": []}')


def test_segmento_missing_inicio_raises() -> None:
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload('{"fin": "00:01:05:00"}', "[]"))
    assert "inicio" in str(exc_info.value)
    assert exc_info.value.path == ("segmento",)


def test_action_not_object_raises() -> None:
    with pytest.raises(SchemaValidationError):
        parse_llm_output(_payload(_segmento(), "[5]"))


def test_corte_rango_not_object_raises() -> None:
    accion = '{"tipo": "corte", "rango": 5, "motivo": "x"}'
    with pytest.raises(SchemaValidationError):
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))


def test_corte_rango_missing_fin_raises() -> None:
    accion = (
        '{"tipo": "corte", "rango": {"inicio": "00:01:00:00"}, "motivo": "x"}'
    )
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))
    assert "fin" in str(exc_info.value)


def test_motion_graphic_missing_required_field_raises() -> None:
    accion = (
        '{"tipo": "motion_graphic", "timestamp": "00:01:00:00", "template": "t",'
        ' "parametros": {}}'
    )
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))
    assert "duracion_frames" in str(exc_info.value)


def test_bad_timecode_format_falls_back_to_schema_error() -> None:
    # Structurally valid but a timecode fails the schema pattern -> fallback path.
    accion = (
        '{"tipo": "corte", "rango": {"inicio": "bad", "fin": "00:01:01:00"},'
        ' "motivo": "x"}'
    )
    with pytest.raises(SchemaValidationError) as exc_info:
        parse_llm_output(_payload(_segmento(), f"[{accion}]"))
    assert "rango" in str(exc_info.value)


def test_package_exports_public_api() -> None:
    from davinci_automation import (
        Corte,
        JsonParseError,
        LlmOutput,
        LlmOutputError,
        MotionGraphic,
        SchemaValidationError,
        Segmento,
        TimecodeError,
        parse_llm_output,
    )

    assert callable(parse_llm_output)
    assert issubclass(LlmOutputError, Exception)
    assert issubclass(JsonParseError, LlmOutputError)
    assert issubclass(SchemaValidationError, LlmOutputError)
    assert issubclass(TimecodeError, LlmOutputError)
    assert Corte.__name__ == "Corte"
    assert Segmento.__name__ == "Segmento"
    assert MotionGraphic.__name__ == "MotionGraphic"
    assert LlmOutput.__name__ == "LlmOutput"