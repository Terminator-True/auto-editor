"""Registry merge utilities: move duplicates into primary event and archive duplicates.

This module provides merge_events(primary_event_id, duplicate_event_ids, dry_run=False).
It performs filesystem moves, updates embeddings, and writes audit logs.
"""
from __future__ import annotations

import os
import shutil
import json
import getpass
import datetime
import logging
from typing import List

logger = logging.getLogger(__name__)


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def merge_events(game: str, primary_event_id: str, duplicate_event_ids: List[str], dry_run: bool = False):
    """Merge duplicates into primary event.

    Moves thumbnails and embeddings, updates registry JSON, rebuilds index async (trigger).
    """
    registry_path = os.path.join("event_registry", f"{game}", "registry.json")
    if not os.path.exists(registry_path):
        raise FileNotFoundError(registry_path)

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    primary = registry.get(primary_event_id)
    if primary is None:
        raise KeyError(primary_event_id)

    audit = {
        "primary": primary_event_id,
        "duplicates": duplicate_event_ids,
        "actor": getpass.getuser(),
        "when": datetime.datetime.utcnow().isoformat() + "Z",
    }

    ops = []
    for dup in duplicate_event_ids:
        entry = registry.get(dup)
        if not entry:
            ops.append({"dup": dup, "status": "missing_in_registry"})
            continue
        # thumbnails
        thumbs_src = os.path.join("event_registry", game, "thumbnails", dup)
        thumbs_dst = os.path.join("event_registry", game, "thumbnails", primary_event_id)
        emb_src = os.path.join("event_registry", "embeddings", f"{dup}.npy")
        emb_dst = os.path.join("event_registry", "embeddings", f"{primary_event_id}.npy")

        ops.append({"dup": dup, "thumbs_src": thumbs_src, "thumbs_dst": thumbs_dst, "emb_src": emb_src, "emb_dst": emb_dst})

        if not dry_run:
            # move thumbnails if exist
            if os.path.exists(thumbs_src):
                _ensure_dir(thumbs_dst)
                for fname in os.listdir(thumbs_src):
                    shutil.move(os.path.join(thumbs_src, fname), os.path.join(thumbs_dst, fname))
                try:
                    os.rmdir(thumbs_src)
                except Exception:
                    pass

            # merge embeddings: for safety we append duplicates to primary numpy array by rebuilding index later
            if os.path.exists(emb_src):
                # move/rename embedding file into primary namespace by creating archive entry
                archive_dir = os.path.join("event_registry", "archive")
                _ensure_dir(archive_dir)
                shutil.move(emb_src, os.path.join(archive_dir, f"{dup}.npy"))

            # archive duplicate event JSON
            ev_src = os.path.join("event_registry", game, "events", f"{dup}.json")
            ev_archive_dir = os.path.join("event_registry", "archive", game)
            _ensure_dir(ev_archive_dir)
            if os.path.exists(ev_src):
                shutil.move(ev_src, os.path.join(ev_archive_dir, f"{dup}.json"))

            # remove from registry
            registry.pop(dup, None)

    # update registry on disk
    if not dry_run:
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    # write audit log
    audit_dir = os.path.join("event_registry", "audit")
    _ensure_dir(audit_dir)
    audit_path = os.path.join(audit_dir, f"merge_{primary_event_id}_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json")
    if not dry_run:
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2)

    # trigger index rebuild by touch file
    trigger = os.path.join("event_registry", "rebuild_trigger.txt")
    if not dry_run:
        with open(trigger, "a", encoding="utf-8") as f:
            f.write(json.dumps({"when": datetime.datetime.utcnow().isoformat(), "primary": primary_event_id}) + "\n")

    return {"ops": ops, "audit": audit, "dry_run": dry_run}
