TESTING — event-categorization slice 1

This document contains exact commands and environment tips to run the tests for the
event-categorization slice (sampling + pipeline stub).

Local environment (Windows / cross-platform)

1) Use Python 3.12 for test runs. Activate your venv that uses Python 3.12 (example):

   - Windows (PowerShell):
     py -3.12 -m venv .venv
     .\.venv\Scripts\Activate.ps1

   - macOS / Linux (bash):
     python3.12 -m venv .venv
     source .venv/bin/activate

2) Install test runner (do NOT modify global requirements from this script). Recommended:

   python -m pip install --upgrade pip
   python -m pip install pytest

3) Run the full test suite (recommended):

   py -3.12 -m pytest -q

   Or run a single test file:

   py -3.12 -m pytest -q tests/test_sampling.py

Notes about ffmpeg

- Tests that exercise real sampling use ffmpeg. The repository contains a Windows
  ffmpeg binary at ./ffmpeg/bin/ffmpeg.exe that tests reference in CI or local runs.
- On CI, ensure ffmpeg is available on PATH or point tests to the shipped binary. Example
  (PowerShell): $env:PATH = "${PWD}\ffmpeg\bin;" + $env:PATH
- If CI cannot provide a binary, prefer mocking ffmpeg calls in tests instead of relying
  on the system ffmpeg. See tests/fixtures/README.txt for fixtures used by sampling tests.

Running tests under CI

- Use the same exact command the repo uses locally in CI: py -3.12 -m pytest -q
- Ensure the CI runner uses Python 3.12 (or set up a matrix with 3.12). On hosted runners
  add a step to install ffmpeg or add the provided ./ffmpeg/bin path to PATH prior to running pytest.

Reproducing the sampling test locally (quick steps)

1) Activate Python 3.12 virtualenv (see above).
2) Install pytest: python -m pip install pytest
3) Ensure ffmpeg is available:
   - Either add ./ffmpeg/bin to PATH (Windows) or install ffmpeg via package manager
   - Or edit tests/test_sampling.py to point to an alternate ffmpeg binary location
4) Run:
   py -3.12 -m pytest -q tests/test_sampling.py::test_sample_frames

Dev / repo guidance

- We recommend adding pytest to dev requirements (e.g., requirements-dev.txt) so CI can
  install it deterministically. This change was NOT made automatically by the apply step;
  please add it explicitly if you want the project to run tests in CI.

Troubleshooting

- If tests fail due to ffmpeg path issues on Windows, make sure the test picks up
  ./ffmpeg/bin/ffmpeg.exe or set PATH as shown above.
- On CI, avoid installing system-wide ffmpeg unless runner supports it; add the repo
  ffmpeg binary or mock ffmpeg calls in tests.
