Slice 3: Embeddings + ANN fast-path

Files added:
- event_categorization/embeddings.py
- event_categorization/ann_index.py
- event_categorization/cache.py
- tests/test_embeddings.py
- tests/test_ann.py
- tests/test_cache.py
- tests/test_fast_path_integration.py

Notes:
- Implements fallback strategies when sentence-transformers/faiss/annoy are unavailable.
- Tests mock heavy dependencies and keep runtime short.
