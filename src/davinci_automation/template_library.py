"""Offline template library for parametrizable motion graphics (Slice 1).

Templates ship as package-data JSON under ``templates/``: a thin ``manifest.json``
index plus one definition file per template holding its exposed param schema
(name, type, default, optional bounds). Loading mirrors the frozen
``schemas/llm_output.v1.json`` pattern via ``importlib.resources`` so templates
are addable/editable by editing JSON only — no orchestrator code change (§3.4).

``TemplateLibrary.load()`` reads the manifest and every definition eagerly and
returns a validated library, raising a typed ``TemplateError`` on malformed
data. ``resolve_template(name)`` returns the matching ``Template`` or ``None``
(no crash) so the applier can map ``None`` to a typed rejection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, Optional

# Supported param type vocabulary (§3.4: string|int|number).
_PARAM_TYPES = ("string", "int", "number")


class TemplateError(Exception):
    """Base error for template manifest/definition loading failures."""


class ManifestError(TemplateError):
    """The template manifest is missing, invalid, or inconsistent."""


class DefinitionError(TemplateError):
    """A template definition file is malformed or inconsistent."""


@dataclass(frozen=True)
class ParamSpec:
    """Schema for one template parameter: type, default, and optional bounds."""

    name: str
    type: str  # "string" | "int" | "number"
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None


@dataclass(frozen=True)
class Template:
    """A resolvable template and its exposed param schemas."""

    id: str
    name: str
    params: Dict[str, ParamSpec]


@dataclass(frozen=True)
class TemplateLibrary:
    """Validated collection of templates, keyed by template id."""

    templates: Dict[str, Template] = field(default_factory=dict)

    @staticmethod
    def load(
        dir: Optional[Path] = None,
        manifest: Optional[Path] = None,
    ) -> "TemplateLibrary":
        """Load the manifest and all template definitions.

        When ``dir`` is omitted, the package's ``templates/`` folder is read via
        ``importlib.resources`` (package data). ``manifest`` overrides the
        manifest location; definitions are still resolved from ``dir``.
        """
        if dir is not None:
            base = Path(dir)
        else:
            base = files("davinci_automation").joinpath("templates")

        manifest_path = Path(manifest) if manifest is not None else base.joinpath("manifest.json")
        entries = _read_json(manifest_path, "manifest", ManifestError)
        if not isinstance(entries, list):
            raise ManifestError(
                f"manifest {manifest_path} must be a JSON array of template entries"
            )

        templates: Dict[str, Template] = {}
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ManifestError(f"manifest entry #{index} must be an object")
            tpl_id = entry.get("id")
            name = entry.get("name")
            file_name = entry.get("file")
            if not all(isinstance(v, str) and v for v in (tpl_id, name, file_name)):
                raise ManifestError(
                    f"manifest entry #{index} must have non-empty string id/name/file"
                )
            if tpl_id in templates:
                raise ManifestError(f"duplicate template id {tpl_id!r} in manifest")

            definition = _read_json(
                base.joinpath(file_name), f"template {tpl_id!r}", DefinitionError
            )
            templates[tpl_id] = _parse_definition(definition, tpl_id)

        return TemplateLibrary(templates=templates)

    def resolve_template(self, name: str) -> Optional[Template]:
        """Return the template matching ``name`` (by id, then by display name),
        or ``None`` when unknown (never raises)."""
        if name in self.templates:
            return self.templates[name]
        for tpl in self.templates.values():
            if tpl.name == name:
                return tpl
        return None


def _read_json(path, what: str, error_cls) -> Any:
    """Read and parse ``path``, raising ``error_cls`` on missing/invalid data."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise error_cls(f"{what} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise error_cls(f"{what} is not valid JSON: {path}") from exc


def _parse_definition(defn: Any, expected_id: str) -> Template:
    if not isinstance(defn, dict):
        raise DefinitionError("template definition must be an object")
    tpl_id = defn.get("id")
    name = defn.get("name")
    params_raw = defn.get("params")
    if not isinstance(tpl_id, str) or not tpl_id:
        raise DefinitionError("template definition missing non-empty string 'id'")
    if tpl_id != expected_id:
        raise DefinitionError(
            f"definition id {tpl_id!r} does not match manifest id {expected_id!r}"
        )
    if not isinstance(name, str) or not name:
        raise DefinitionError(f"template {tpl_id!r}: missing non-empty string 'name'")
    if not isinstance(params_raw, dict) or not params_raw:
        raise DefinitionError(f"template {tpl_id!r}: 'params' must be a non-empty mapping")

    params: Dict[str, ParamSpec] = {}
    for pname, pdata in params_raw.items():
        params[pname] = _parse_param(tpl_id, pname, pdata)
    return Template(id=tpl_id, name=name, params=params)


def _parse_param(tpl_id: str, pname: str, pdata: Any) -> ParamSpec:
    if not isinstance(pdata, dict):
        raise DefinitionError(f"template {tpl_id!r} param {pname!r} must be an object")
    ptype = pdata.get("type")
    if ptype not in _PARAM_TYPES:
        raise DefinitionError(
            f"template {tpl_id!r} param {pname!r}: invalid type {ptype!r} "
            f"(expected one of {', '.join(_PARAM_TYPES)})"
        )
    if "default" not in pdata:
        raise DefinitionError(f"template {tpl_id!r} param {pname!r}: missing 'default'")

    lo = pdata.get("min")
    hi = pdata.get("max")
    for bound, label in ((lo, "min"), (hi, "max")):
        if bound is not None and (isinstance(bound, bool) or not isinstance(bound, (int, float))):
            raise DefinitionError(
                f"template {tpl_id!r} param {pname!r}: '{label}' must be a number"
            )
    return ParamSpec(
        name=pname,
        type=ptype,
        default=pdata["default"],
        min=float(lo) if lo is not None else None,
        max=float(hi) if hi is not None else None,
    )