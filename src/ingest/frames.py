from typing import Dict, Any, Optional
import logging

from ..storage.metadata_store import MetadataStore, FileMetadataStore
from ..analysis import moondream_classifier
from .worker import submit as submit_worker

logger = logging.getLogger(__name__)


def _classify_and_persist(frame: Dict[str, Any], classifier, metadata_store: MetadataStore):
    try:
        res = classifier.classify_frame(frame)
        try:
            if metadata_store:
                metadata_store.save_metadata(frame.get("frame_id"), res)
        except Exception:
            logger.exception("failed to persist metadata")
    except Exception:
        logger.exception("classification failed")


def ingest_frame(frame: Dict[str, Any], classifier=None, metadata_store: Optional[MetadataStore] = None, async_worker: bool = True) -> bool:
    """Ingest a single frame. Returns True if ingest proceeds (even if classification fails).

    classifier: object with classify_frame(frame) -> dict
    metadata_store: MetadataStore instance; if None, FileMetadataStore() is used
    async_worker: if True, classification is submitted to background worker; if False, runs synchronously
    """
    if metadata_store is None:
        metadata_store = FileMetadataStore()

    # Ensure ingest proceeds even if classifier fails
    if classifier is None:
        # nothing to do, proceed
        return True

    if async_worker:
        try:
            submit_worker(_classify_and_persist, frame, classifier, metadata_store)
        except Exception:
            # fallback to sync
            logger.exception("async worker submit failed, falling back to sync classification")
            _classify_and_persist(frame, classifier, metadata_store)
    else:
        _classify_and_persist(frame, classifier, metadata_store)

    return True
