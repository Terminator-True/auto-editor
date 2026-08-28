"""Thin standalone entry point for the DaVinci Resolve automation orchestrator."""

import sys
from pathlib import Path

# Make the src-layout package importable when run uninstalled from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from davinci_automation.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())