"""Tests for the offline template library (Slice 1).

Covers ``TemplateLibrary.load`` (package-data + explicit dir), param-schema
exposure, malformed manifest/definition handling, unknown-template resolution,
and template discovery without code change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from davinci_automation.template_library import (
    DefinitionError,
    ManifestError,
    TemplateError,
    TemplateLibrary,
)

LOWER_THIRD = {
    "id": "lower_third",
    "name": "Lower Third",
    "params": {
        "texto": {"type": "string", "default": ""},
        "color": {"type": "string", "default": "white"},
        "duracion": {"type": "int", "default": 60, "min": 1, "max": 240},
        "posicion": {"type": "string", "default": "bottom"},
    },
}


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_library(tmp_path: Path, templates) -> Path:
    entries = []
    for tpl in templates:
        _write_json(tmp_path / f"{tpl['id']}.json", tpl)
        entries.append(
            {"id": tpl["id"], "name": tpl["name"], "file": f"{tpl['id']}.json"}
        )
    _write_json(tmp_path / "manifest.json", entries)
    return tmp_path


# ---- spec: Manifest lists all templates -------------------------------------

def test_load_from_package_data_exposes_all_templates() -> None:
    lib = TemplateLibrary.load()
    assert set(lib.templates) == {"lower_third", "title", "callout"}


# ---- spec: Param schema present per template --------------------------------

def test_param_schema_carries_type_default_and_bounds() -> None:
    lib = TemplateLibrary.load()
    lower = lib.templates["lower_third"]
    texto = lower.params["texto"]
    assert texto.type == "string"
    assert texto.default == ""
    duracion = lower.params["duracion"]
    assert duracion.type == "int"
    assert duracion.default == 60
    assert duracion.min == 1
    assert duracion.max == 240
    assert lower.params["color"].default == "white"
    assert lower.params["posicion"].type == "string"


# ---- spec: Malformed manifest / unknown template ----------------------------

def test_malformed_manifest_not_a_list_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", {"not": "a list"})
    with pytest.raises(ManifestError):
        TemplateLibrary.load(dir=tmp_path)


def test_malformed_definition_raises(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "manifest.json",
        [{"id": "x", "name": "X", "file": "x.json"}],
    )
    _write_json(
        tmp_path / "x.json",
        {"id": "x", "name": "X", "params": {"p": {"type": "bogus"}}},
    )
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_missing_definition_file_raises(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "manifest.json",
        [{"id": "x", "name": "X", "file": "missing.json"}],
    )
    with pytest.raises(TemplateError):
        TemplateLibrary.load(dir=tmp_path)


def test_unknown_template_resolves_to_none(tmp_path: Path) -> None:
    _make_library(tmp_path, [LOWER_THIRD])
    lib = TemplateLibrary.load(dir=tmp_path)
    assert lib.resolve_template("intro_banner") is None


def test_resolve_template_by_id(tmp_path: Path) -> None:
    _make_library(tmp_path, [LOWER_THIRD])
    lib = TemplateLibrary.load(dir=tmp_path)
    assert lib.resolve_template("lower_third").name == "Lower Third"


# ---- spec: Templates addable without code change ----------------------------

def test_new_template_discoverable_after_reload(tmp_path: Path) -> None:
    _make_library(tmp_path, [LOWER_THIRD])
    lib = TemplateLibrary.load(dir=tmp_path)
    assert lib.resolve_template("intro_banner") is None

    new = {
        "id": "intro_banner",
        "name": "Intro Banner",
        "params": {"texto": {"type": "string", "default": "Hi"}},
    }
    _write_json(tmp_path / "intro_banner.json", new)
    entries = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    entries.append(
        {"id": "intro_banner", "name": "Intro Banner", "file": "intro_banner.json"}
    )
    _write_json(tmp_path / "manifest.json", entries)

    lib2 = TemplateLibrary.load(dir=tmp_path)
    tpl = lib2.resolve_template("intro_banner")
    assert tpl is not None
    assert tpl.name == "Intro Banner"
    assert tpl.params["texto"].default == "Hi"


# ---- triangulation: manifest entry edge cases -------------------------------

def test_manifest_entry_not_an_object_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", ["not-an-object"])
    with pytest.raises(ManifestError):
        TemplateLibrary.load(dir=tmp_path)


def test_manifest_entry_missing_field_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X"}])
    with pytest.raises(ManifestError):
        TemplateLibrary.load(dir=tmp_path)


def test_duplicate_template_id_raises(tmp_path: Path) -> None:
    entry = {"id": "x", "name": "X", "file": "x.json"}
    _write_json(
        tmp_path / "x.json",
        {"id": "x", "name": "X", "params": {"texto": {"type": "string", "default": ""}}},
    )
    _write_json(tmp_path / "manifest.json", [entry, entry])
    with pytest.raises(ManifestError):
        TemplateLibrary.load(dir=tmp_path)


def test_invalid_manifest_json_raises(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(ManifestError):
        TemplateLibrary.load(dir=tmp_path)


def test_resolve_by_display_name(tmp_path: Path) -> None:
    _make_library(tmp_path, [LOWER_THIRD])
    lib = TemplateLibrary.load(dir=tmp_path)
    assert lib.resolve_template("Lower Third").id == "lower_third"


# ---- triangulation: definition edge cases -----------------------------------

def test_definition_not_an_object_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", [1, 2])
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_definition_missing_id_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", {"name": "X", "params": {}})
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_definition_id_mismatch_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", {"id": "y", "name": "X", "params": {"p": {"type": "string", "default": ""}}})
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_definition_missing_name_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", {"id": "x", "params": {"p": {"type": "string", "default": ""}}})
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_definition_empty_params_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", {"id": "x", "name": "X", "params": {}})
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_param_not_an_object_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", {"id": "x", "name": "X", "params": {"p": "str"}})
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_param_missing_default_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(tmp_path / "x.json", {"id": "x", "name": "X", "params": {"p": {"type": "string"}}})
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)


def test_param_invalid_bound_raises(tmp_path: Path) -> None:
    _write_json(tmp_path / "manifest.json", [{"id": "x", "name": "X", "file": "x.json"}])
    _write_json(
        tmp_path / "x.json",
        {"id": "x", "name": "X", "params": {"p": {"type": "int", "default": 1, "min": "lo"}}},
    )
    with pytest.raises(DefinitionError):
        TemplateLibrary.load(dir=tmp_path)