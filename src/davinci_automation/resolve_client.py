"""Thin wrapper around the ``DaVinciResolveScript`` module.

The scripting module only exists inside Resolve's own Python environment, so the
bridge is loaded through a configurable path with a platform-default fallback.
Connection and read failures map to typed exceptions so the CLI can log them
cleanly without raw tracebacks.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import List, Optional


class ResolveScriptNotFound(Exception):
    """Raised when ``DaVinciResolveScript`` cannot be imported."""


class ResolveNotRunning(Exception):
    """Raised when the module imports but no Resolve instance is reachable."""


class NoOpenProject(Exception):
    """Raised when Resolve is running but no project is open."""


class NoActiveTimeline(Exception):
    """Raised when a project is open but has no active timeline."""


# Platform-default directories probed when no script_path is configured.
PLATFORM_MODULE_DIRS: List[Path] = [
    Path("/opt/resolve/Developer/Scripting/Modules"),  # Linux
    Path(os.environ.get("PROGRAMDATA", ""))
    / "Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules",  # Windows
    Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"),  # macOS
]

_ACTIONABLE_MESSAGE = (
    "DaVinciResolveScript was not found on the Python path. Set "
    "'resolve.script_path' in config.yaml to the directory containing the "
    "DaVinciResolveScript module, or ensure Resolve is installed in a default "
    "location so it can be auto-detected."
)


class ResolveClient:
    """Read-only facade over a connected DaVinci Resolve instance."""

    def __init__(self, script_path: Optional[str] = None, detect_version: bool = True) -> None:
        self.script_path = Path(script_path) if script_path else None
        self.detect_version = detect_version
        self._script_module: Optional[object] = None
        self._resolve: Optional[object] = None

    # -- script loading ----------------------------------------------------

    def load_script(self) -> object:
        """Import ``DaVinciResolveScript``.

        Loader order (per design): configured ``script_path`` -> default import
        -> platform-default directories. Raises ``ResolveScriptNotFound``.
        """
        if self.script_path is not None:
            if not self.script_path.is_dir():
                raise ResolveScriptNotFound(
                    f"configured resolve.script_path does not exist: {self.script_path}"
                )
            sys.path.insert(0, str(self.script_path))

        try:
            module = importlib.import_module("DaVinciResolveScript")
        except ModuleNotFoundError:
            module = self._probe_platform_defaults()
            if module is None:
                raise ResolveScriptNotFound(_ACTIONABLE_MESSAGE) from None

        self._script_module = module
        return module

    def _probe_platform_defaults(self) -> Optional[object]:
        for directory in PLATFORM_MODULE_DIRS:
            if not directory.is_dir():
                continue
            sys.path.insert(0, str(directory))
            try:
                return importlib.import_module("DaVinciResolveScript")
            except ModuleNotFoundError:
                continue
        return None

    # -- connection --------------------------------------------------------

    def connect(self) -> object:
        """Connect to the running Resolve instance.

        Returns the Resolve object. Raises ``ResolveNotRunning`` when the module
        imports but no instance is reachable.
        """
        if self._script_module is None:
            self.load_script()

        try:
            resolve = self._script_module.scriptapp("Resolve")
        except Exception as exc:  # noqa: BLE001 - API raises opaque errors
            raise ResolveNotRunning(
                "could not reach DaVinci Resolve; make sure the GUI is running "
                "with a project open"
            ) from exc

        if resolve is None:
            raise ResolveNotRunning(
                "DaVinci Resolve is not running; start the application and open "
                "a project before running the orchestrator"
            )

        self._resolve = resolve
        return resolve

    def get_version(self) -> Optional[str]:
        """Return the Resolve version string, or ``None`` if unavailable."""
        try:
            return str(self._resolve.GetVersionString())
        except Exception:  # noqa: BLE001 - version is best-effort
            return None

    # -- reads -------------------------------------------------------------

    def active_project(self) -> object:
        """Return the active project; raise ``NoOpenProject`` if none open."""
        project_manager = self._resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        if project is None:
            raise NoOpenProject("no project is open in DaVinci Resolve")
        return project

    def active_timeline(self) -> object:
        """Return the active timeline; raise ``NoActiveTimeline`` if absent."""
        project = self.active_project()
        timeline = project.GetCurrentTimeline()
        if timeline is None:
            raise NoActiveTimeline("the active project has no active timeline")
        return timeline