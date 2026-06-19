# Event Categorization Integration Test Setup

These instructions explain how to run the integration tests for the event-categorization pipeline.

Required environment variables (for real integration):
- HF_TOKEN — Hugging Face token if you want to enable HF Text-LM wrapper
- OPENAI_API_KEY — OpenAI API key for embeddings
- RUN_REAL_INTEGRATION=1 — set to run integration tests

Install optional dependencies:
- pip install -U "sentence-transformers" "transformers" "torch"  # for local embeddings/LM
- pip install -U openai  # for OpenAI embeddings

Run tests:
- py -3.12 -m pytest -q
- To run only the integration test: RUN_REAL_INTEGRATION=1 py -3.12 -m pytest tests/test_text_classifier_integration.py -q

If dependencies are not installed, the code falls back to deterministic embeddings and the TextLMWrapper will return predictable dummy results.
