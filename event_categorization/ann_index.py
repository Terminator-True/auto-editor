import os
import threading
import math
from typing import List, Tuple, Optional

_lock = threading.RLock()


class ANNIndex:
    def __init__(self, dim: int = 384, backend: Optional[str] = None, game: str = "default"):
        self.dim = dim
        self.backend = backend
        self.game = game
        self._ids = []
        self._embs = []  # list of lists
        self._index = None
        self._built = False

    def add(self, event_id: str, embedding: List[float]):
        with _lock:
            self._ids.append(event_id)
            self._embs.append(embedding)
            self._built = False

    def build_index(self):
        """Attempt FAISS, then Annoy, else keep brute-force list."""
        with _lock:
            try:
                import faiss
                import numpy as _np
                xb = _np.array(self._embs, dtype=_np.float32)
                self._index = faiss.IndexFlatL2(self.dim)
                self._index.add(xb)
                self._built = True
                self.backend = "faiss"
                return
            except Exception:
                pass

            try:
                from annoy import AnnoyIndex
                u = AnnoyIndex(self.dim, "euclidean")
                for i, v in enumerate(self._embs):
                    u.add_item(i, v)
                u.build(10)
                self._index = u
                self._built = True
                self.backend = "annoy"
                return
            except Exception:
                pass

            # fallback: brute force kept in memory
            self._index = None
            self._built = True
            self.backend = "bruteforce"

    def query(self, embedding: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        with _lock:
            if not self._built:
                self.build_index()

            if self.backend == "faiss":
                import numpy as _np
                xb = _np.array([embedding], dtype=_np.float32)
                D, I = self._index.search(xb, top_k)
                res = []
                for dist, idx in zip(D[0], I[0]):
                    if idx < 0 or idx >= len(self._ids):
                        continue
                    res.append((self._ids[int(idx)], float(dist)))
                return res

            if self.backend == "annoy":
                ids = self._index.get_nns_by_vector(embedding, top_k, include_distances=True)
                idxs, dists = ids
                return [(self._ids[i], float(dists[idxs.index(i)])) for i in idxs]

            # brute force
            def _dist(a, b):
                return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

            scored = [(i, _dist(embedding, e)) for i, e in enumerate(self._embs)]
            scored.sort(key=lambda x: x[1])
            return [(self._ids[i], d) for i, d in scored[:top_k]]

    def save(self, base_path: Optional[str] = None):
        base = base_path or os.path.join("event_registry", "index", self.game)
        os.makedirs(base, exist_ok=True)
        # save ids and embeddings as numpy if possible
        try:
            import numpy as _np
            _np.save(os.path.join(base, "ids.npy"), _np.array(self._ids, dtype=object))
            _np.save(os.path.join(base, "embs.npy"), _np.array(self._embs, dtype=_np.float32))
        except Exception:
            # fallback textual
            with open(os.path.join(base, "ids.txt"), "w", encoding="utf-8") as f:
                for i in self._ids:
                    f.write(i + "\n")
            with open(os.path.join(base, "embs.txt"), "w", encoding="utf-8") as f:
                for e in self._embs:
                    f.write(",".join(map(str, e)) + "\n")

    @classmethod
    def load(cls, game: str = "default", dim: int = 384, base_path: Optional[str] = None):
        base = base_path or os.path.join("event_registry", "index", game)
        inst = cls(dim=dim, game=game)
        try:
            import numpy as _np
            ids = _np.load(os.path.join(base, "ids.npy"), allow_pickle=True).tolist()
            embs = _np.load(os.path.join(base, "embs.npy")).tolist()
            inst._ids = ids
            inst._embs = embs
            inst._built = False
            return inst
        except Exception:
            # try textual
            try:
                ids = []
                embs = []
                with open(os.path.join(base, "ids.txt"), "r", encoding="utf-8") as f:
                    ids = [l.strip() for l in f.readlines() if l.strip()]
                with open(os.path.join(base, "embs.txt"), "r", encoding="utf-8") as f:
                    for l in f:
                        embs.append([float(x) for x in l.strip().split(",") if x.strip()])
                inst._ids = ids
                inst._embs = embs
                inst._built = False
                return inst
            except Exception:
                # empty index
                return inst
