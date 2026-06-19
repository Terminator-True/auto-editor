"""Shim CLI for scripts.event_registry_cli delegating to event_categorization.registry.cli

This module preserves the entrypoint so `python -m scripts.event_registry_cli --help`
continues to function. If the canonical CLI is absent, the shim provides a
minimal --help and exits gracefully.
"""
import sys

try:
    # Prefer explicit CLI main if available
    from event_categorization.registry.cli import main as _canonical_main
except Exception:  # pragma: no cover - defensive
    _canonical_main = None


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if _canonical_main is None:
        # Minimal fallback: support --help
        if any(a in ("-h", "--help") for a in argv):
            print("Usage: python -m scripts.event_registry_cli [--help]\n\nThis is a compatibility shim. The canonical CLI (event_categorization.registry.cli) is unavailable.")
            return 0
        raise NotImplementedError("Canonical CLI not found: event_categorization.registry.cli")
    # Delegate to canonical implementation
    return _canonical_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
