Moondream Classifier Integration

Overview
- The Moondream classifier uses Ollama to classify frames and persists metadata via a pluggable MetadataStore.

Acceptance checklist
- [ ] Ingest frames trigger classifier
- [ ] Classifier calls Ollama client
- [ ] Results are calibrated and stored
- [ ] Telemetry counters increment
- [ ] E2E integration test (mocked Ollama) passes

Basic config
- calibration parameters live in config/calibration.yml
