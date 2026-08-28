"""Offline, non-destructive motion-graphics applier (Slice 2).

``MotionGraphicApplier.appraise`` turns a validated ``MotionGraphic`` LLM action
(``llm_schema.MotionGraphic``) into an ``InsertionDecision``: which template,
validated param values, timestamp, and duration. It is deliberately
non-destructive — it only audits its decision (or typed rejection) through the
injected ``JsonlLogger`` and never mutates any clip/track/marker/timeline. The
decision is a frozen dataclass so it can be safely stored/handled downstream
while actual Fusion authoring stays out of scope (needs a live Resolve).

Typed rejections mirror the design vocabulary:
``template_rejected`` (unknown template), ``param_rejected`` (schema/bounds
mismatch), ``range_rejected`` (timestamp + duration outside the timeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from davinci_automation.jsonl_logger import JsonlLogger
from davinci_automation.llm_schema import MotionGraphic
from davinci_automation.orchestrator import validate_range
from davinci_automation.template_library import ParamSpec, Template, TemplateLibrary

# Decision kinds (design vocabulary).
INTENDED_MOTION_GRAPHIC = "intended_motion_graphic"
TEMPLATE_REJECTED = "template_rejected"
PARAM_REJECTED = "param_rejected"
RANGE_REJECTED = "range_rejected"


@dataclass(frozen=True)
class InsertionDecision:
    """A validated (or rejected) motion-graphics insertion decision.

    ``valid`` is True only for ``intended_motion_graphic``; every rejection has
    ``valid=False`` and a non-empty ``reason``. ``timestamp``/``duration`` are
    expressed in frames (via ``Timecode.total_frames``).
    """

    valid: bool
    kind: str
    template_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None
    duration: Optional[int] = None
    reason: str = field(default="")


class MotionGraphicApplier:
    """Validate a ``MotionGraphic`` against a ``TemplateLibrary`` + timeline.

    The library is injected (default ``TemplateLibrary.load()``) so the applier
    is fully offline-testable and a config-driven library can be supplied by the
    CLI/orchestrator.
    """

    def __init__(self, library: TemplateLibrary) -> None:
        self.library = library

    def appraise(
        self, mg: MotionGraphic, duration: int, logger: JsonlLogger
    ) -> InsertionDecision:
        """Return the insertion decision for ``mg``, auditing it via ``logger``.

        Never raises for the handled rejection cases and never mutates any
        timeline. ``duration`` is the timeline's frame length.
        """
        template = self.library.resolve_template(mg.template)
        if template is None:
            return self._reject(
                logger,
                kind=TEMPLATE_REJECTED,
                reason=f"unknown template {mg.template!r}",
                template=mg.template,
            )

        params, problem = _validate_params(template, mg.parametros)
        if problem is not None:
            param_name, why = problem
            logger.write(
                PARAM_REJECTED,
                "error",
                template=template.id,
                param=param_name,
                reason=why,
            )
            return InsertionDecision(
                valid=False,
                kind=PARAM_REJECTED,
                template_id=template.id,
                params=None,
                timestamp=None,
                duration=None,
                reason=why,
            )

        start = mg.timestamp.total_frames
        end = start + mg.duracion_frames
        if not validate_range(start, end, duration):
            reason = (
                f"motion graphic at frame {start} for {mg.duracion_frames} frames "
                f"is outside timeline duration {duration}"
            )
            logger.write(
                RANGE_REJECTED,
                "error",
                template=template.id,
                timestamp=start,
                duration=mg.duracion_frames,
                timeline_duration=duration,
                reason=reason,
            )
            return InsertionDecision(
                valid=False,
                kind=RANGE_REJECTED,
                template_id=template.id,
                params=params,
                timestamp=start,
                duration=mg.duracion_frames,
                reason=reason,
            )

        logger.write(
            INTENDED_MOTION_GRAPHIC,
            "info",
            template_id=template.id,
            params=params,
            timestamp=start,
            duration=mg.duracion_frames,
        )
        return InsertionDecision(
            valid=True,
            kind=INTENDED_MOTION_GRAPHIC,
            template_id=template.id,
            params=params,
            timestamp=start,
            duration=mg.duracion_frames,
        )

    @staticmethod
    def _reject(
        logger: JsonlLogger,
        kind: str,
        reason: str,
        template: Optional[str],
    ) -> InsertionDecision:
        logger.write(kind, "error", template=template, reason=reason)
        return InsertionDecision(
            valid=False,
            kind=kind,
            template_id=None,
            params=None,
            timestamp=None,
            duration=None,
            reason=reason,
        )


def _validate_params(
    template: Template, parametros: Dict[str, Any]
) -> tuple[Dict[str, Any], Optional[tuple[str, str]]]:
    """Validate ``parametros`` against ``template.params``.

    Returns ``(effective_params, None)`` on success where ``effective_params``
    merges schema defaults with the provided, validated values; or
    ``(params_so_far, (param_name, why))`` on the first mismatch. Unprovided
    params fall back to their schema default.
    """
    effective: Dict[str, Any] = {name: spec.default for name, spec in template.params.items()}

    for name, value in parametros.items():
        spec = template.params.get(name)
        if spec is None:
            return effective, (name, f"unknown parameter {name!r} for template {template.id!r}")
        if not _type_ok(spec.type, value):
            return effective, (
                name,
                f"parameter {name!r} expects {spec.type}, got {type(value).__name__}",
            )
        if spec.min is not None and value < spec.min:
            return effective, (name, f"parameter {name!r} value {value} below min {spec.min}")
        if spec.max is not None and value > spec.max:
            return effective, (name, f"parameter {name!r} value {value} above max {spec.max}")
        effective[name] = value

    return effective, None


def _type_ok(ptype: str, value: Any) -> bool:
    """True when ``value`` matches the param ``type`` vocabulary (no coercion)."""
    if ptype == "string":
        return isinstance(value, str)
    if ptype == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if ptype == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


# Re-export the schema types referenced by the applier's public contract.
__all__ = [
    "InsertionDecision",
    "MotionGraphicApplier",
    "ParamSpec",
    "Template",
]