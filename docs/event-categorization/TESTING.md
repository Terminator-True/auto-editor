Quick testing notes for event-categorization slice 2

Tests added:
- tests/test_template_matching.py — unit test for analyze_timestamp with monkeypatched TemplateDetector and VisionLLMWrapper
- tests/test_e2e_template.py — lightweight end-to-end pipeline test that mocks model loads

Run locally:
1) Activate venv (Python 3.12)
2) pip install pytest pillow
3) py -3.12 -m pytest -q

Notes:
- Tests avoid heavy downloads by mocking VisionLLMWrapper._ensure_detector and classify_frame/analyze_frame.
- Ensure ffmpeg is available on PATH if you remove the monkeypatches that fake frame extraction.

Optional backends for better performance:

- sentence-transformers (text embeddings):
  pip install sentence-transformers

- FAISS (vector index) — on Windows prefer faiss-cpu via conda if available, or use Annoy as fallback:
  conda install -c pytorch faiss-cpu  # recommended on Windows via conda
  OR
  pip install annoy

- OpenAI embeddings fallback: set OPENAI_API_KEY environment variable

CI notes:
- If FAISS wheel is not available on CI, use Annoy or rely on the brute-force fallback. Tests are written to mock heavy deps and should pass without these optional libraries.
