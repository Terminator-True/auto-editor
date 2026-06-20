import json
from pathlib import Path
from typing import Protocol, Any, Dict


class MetadataStore(Protocol):
    def save_metadata(self, frame_id: str, metadata: Dict[str, Any]) -> None:
        ...

    def load_metadata(self, frame_id: str) -> Dict[str, Any]:
        ...


class FileMetadataStore:
    def __init__(self, base_path: str = "var"):
        self.base = Path(base_path)

    def _path_for(self, frame_id: str) -> Path:
        d = self.base / "metadata" / "moondream"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{frame_id}.json"

    def save_metadata(self, frame_id: str, metadata: Dict[str, Any]) -> None:
        p = self._path_for(frame_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(metadata, f)

    def load_metadata(self, frame_id: str) -> Dict[str, Any]:
        p = self._path_for(frame_id)
        if not p.exists():
            raise FileNotFoundError(str(p))
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)


try:
    import psycopg2
    from psycopg2.extras import Json
    HAVE_PG = True
except Exception:
    HAVE_PG = False


class PostgresMetadataStore:
    """Simple Postgres-backed metadata store using JSONB.

    Expects environment variables or connection string in dsn
    """
    def __init__(self, dsn: str):
        if not HAVE_PG:
            raise RuntimeError("psycopg2 not available")
        self.dsn = dsn

    def save_metadata(self, frame_id: str, metadata: Dict[str, Any]) -> None:
        conn = psycopg2.connect(self.dsn)
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS metadata (frame_id text PRIMARY KEY, data jsonb)")
                cur.execute("INSERT INTO metadata (frame_id, data) VALUES (%s, %s) ON CONFLICT (frame_id) DO UPDATE SET data = EXCLUDED.data", (frame_id, Json(metadata)))
                conn.commit()
        finally:
            conn.close()

    def load_metadata(self, frame_id: str) -> Dict[str, Any]:
        conn = psycopg2.connect(self.dsn)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM metadata WHERE frame_id = %s", (frame_id,))
                row = cur.fetchone()
                if not row:
                    raise FileNotFoundError(frame_id)
                return row[0]
        finally:
            conn.close()
