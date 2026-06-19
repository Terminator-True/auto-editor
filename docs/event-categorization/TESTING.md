Clustering and CLI testing notes

- Conservative defaults: min_cluster_size=2, distance_threshold=0.6 to avoid over-merging.
- HDBSCAN is preferred; if unavailable AgglomerativeClustering (sklearn) is used.
- For production, install hdbscan and sklearn: pip install hdbscan scikit-learn
- For process locks, install portalocker: pip install portalocker

Running tests locally:

1. Create virtualenv with Python 3.12 and activate it (env3.12 provided in repo).
2. Install test deps: pip install -r requirements-dev.txt (or at minimum pytest)
3. Run: py -3.12 -m pytest -q

If HDBSCAN/portalocker are not installed, code falls back to conservative alternatives. Tests are written to mock embeddings and avoid heavy deps.
