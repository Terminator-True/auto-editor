"""DaVinci Resolve automation orchestrator — bootstrap slice.

Standalone, read-only connection to a running DaVinci Resolve instance via
``DaVinciResolveScript``, reading the active project/timeline and enumerating
clips and tracks, with externalized YAML config and JSON-lines audit logging.
"""

from davinci_automation.llm_schema import (
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
from davinci_automation.orchestrator import Orchestrator, OrchestratorError
from davinci_automation.srt_reader import SrtError
from davinci_automation.apply import AutoApplier, MarkerApplier
from davinci_automation.motion_graphics import InsertionDecision, MotionGraphicApplier
from davinci_automation.template_library import (
    TemplateError,
    ManifestError,
    DefinitionError,
    TemplateLibrary,
    Template,
    ParamSpec,
)

__version__ = "0.1.0"

__all__ = [
    "parse_llm_output",
    "LlmOutput",
    "Segmento",
    "Corte",
    "MotionGraphic",
    "LlmOutputError",
    "JsonParseError",
    "SchemaValidationError",
    "TimecodeError",
    "Orchestrator",
    "OrchestratorError",
    "SrtError",
    "MarkerApplier",
    "AutoApplier",
    "InsertionDecision",
    "MotionGraphicApplier",
    "TemplateLibrary",
    "Template",
    "ParamSpec",
    "TemplateError",
    "ManifestError",
    "DefinitionError",
]
