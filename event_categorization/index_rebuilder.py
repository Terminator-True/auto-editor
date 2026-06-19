"""Simple async index rebuilder with queue and file lock.

Uses a background thread to process rebuild requests. For process-safe locks,
tries to use portalocker, else falls back to a naive file lock with warnings.
"""
from __future__ import annotations

import threading
import time
import logging
import os
import json
from queue import Queue, Empty

logger = logging.getLogger(__name__)

try:
    import portalocker
except Exception:
    portalocker = None


class IndexRebuilder:
    def __init__(self, game: str = "default"):
        self.game = game
        self._q: "Queue[dict]" = Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop = threading.Event()
        self._thread.start()

    def request_rebuild(self, reason: str = "manual"):
        self._q.put({"when": time.time(), "reason": reason})

    def _acquire_lock(self, timeout: int = 10):
        lockfile = os.path.join("event_registry", "index", f"{self.game}.lock")
        os.makedirs(os.path.dirname(lockfile), exist_ok=True)
        if portalocker is not None:
            f = open(lockfile, "w")
            portalocker.lock(f, portalocker.LOCK_EX)
            return f
        else:
            # naive lock
            start = time.time()
            while True:
                try:
                    fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    return fd
                except FileExistsError:
                    if time.time() - start > timeout:
                        raise TimeoutError("could not acquire lock")
                    time.sleep(0.5)

    def _release_lock(self, handle):
        lockfile = os.path.join("event_registry", "index", f"{self.game}.lock")
        if portalocker is not None:
            try:
                handle.close()
            except Exception:
                pass
        else:
            try:
                os.close(handle)
            except Exception:
                pass
            try:
                os.remove(lockfile)
            except Exception:
                pass

    def _perform_rebuild(self, item):
        # placeholder rebuild: read embeddings and save index file
        try:
            lock = self._acquire_lock()
        except Exception as e:
            logger.error("could not acquire lock for rebuild: %s", e)
            return False
        try:
            # simulate rebuild
            time.sleep(0.1)
            base = os.path.join("event_registry", "index", self.game)
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "rebuilt.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"when": time.time(), "reason": item.get("reason")}, f)
            return True
        finally:
            self._release_lock(lock)

    def _run(self):
        backoff = 1
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=0.5)
            except Empty:
                continue
            success = False
            try:
                success = self._perform_rebuild(item)
            except Exception as e:
                logger.exception("rebuild failed: %s", e)
                success = False

            if not success:
                # exponential backoff requeue
                backoff = min(backoff * 2, 60)
                logger.info("rebuild failed, retrying in %s seconds", backoff)
                time.sleep(backoff)
                self._q.put(item)
            else:
                backoff = 1

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
