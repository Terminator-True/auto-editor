import threading
from typing import Callable, Any


class SimpleWorker:
    """A tiny fire-and-forget worker using threading.Thread.

    Provides submit(func, *args, **kwargs) -> threading.Thread
    """

    def submit(self, func: Callable[..., Any], *args, **kwargs) -> threading.Thread:
        t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        t.start()
        return t


_default_worker = SimpleWorker()


def submit(func: Callable[..., Any], *args, **kwargs) -> threading.Thread:
    return _default_worker.submit(func, *args, **kwargs)
