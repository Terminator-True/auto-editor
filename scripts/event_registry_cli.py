"""CLI for human-in-the-loop event registry review.

This is a small click-based CLI exposing commands used in tests. The backend
operations are separated into functions so tests can mock them.
"""
import json
import os
import sys
import logging
from typing import List

try:
    import click
except Exception:
    click = None  # type: ignore

logger = logging.getLogger(__name__)


def list_suggestions(game: str, limit: int = 10):
    # placeholder: load suggestions from event_registry/suggestions.json
    path = os.path.join("event_registry", "suggestions", f"{game}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data[:limit]


def show_event(event_id: str):
    # simple loader
    path = os.path.join("event_registry", "events", f"{event_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(event_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def review_suggestion_action(suggestion_id: str, approve: bool, merge_into: str = None, dry_run: bool = False):
    # this would call registry.merge_events when approving
    # for now, write a small audit file
    out = {"suggestion_id": suggestion_id, "approve": approve, "merge_into": merge_into, "dry_run": dry_run}
    os.makedirs(os.path.join("event_registry", "reviews"), exist_ok=True)
    with open(os.path.join("event_registry", "reviews", f"{suggestion_id}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f)
    return out


if click:
    @click.group()
    def cli():
        pass

    @cli.command("list-suggestions")
    @click.option("--game", default="default")
    @click.option("--limit", default=10)
    def _list(game, limit):
        res = list_suggestions(game, limit)
        click.echo(json.dumps(res))

    @cli.command("show-event")
    @click.argument("event_id")
    def _show(event_id):
        try:
            ev = show_event(event_id)
            click.echo(json.dumps(ev))
        except FileNotFoundError:
            click.echo("not found", err=True)
            sys.exit(2)

    @cli.command("review-suggestion")
    @click.argument("suggestion_id")
    @click.option("--approve", is_flag=True)
    @click.option("--reject", is_flag=True)
    @click.option("--merge-into", default=None)
    @click.option("--dry-run", is_flag=True)
    def _review(suggestion_id, approve, reject, merge_into, dry_run):
        if approve and reject:
            click.echo("cannot both approve and reject", err=True)
            sys.exit(2)
        action = review_suggestion_action(suggestion_id, approve, merge_into, dry_run)
        click.echo(json.dumps(action))

    @cli.command("export-registry")
    @click.option("--format", "fmt", type=click.Choice(["json", "yaml"]), default="json")
    @click.option("--out", required=True)
    def _export(fmt, out):
        # read event_registry.json from config
        import json as _json
        cfg = _json.load(open("config.json", "r"))
        path = cfg.get("event_registry_path", "./event_registry.json")
        if not os.path.exists(path):
            click.echo("registry not found", err=True)
            sys.exit(2)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if fmt == "json":
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f)
        else:
            try:
                import yaml
                with open(out, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f)
            except Exception:
                click.echo("yaml not available", err=True)
                sys.exit(2)

    if __name__ == "__main__":
        cli()
