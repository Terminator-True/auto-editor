# auto-editor — Event Categorization & Template Learning

Resumen rápido
- auto-editor extrae templates y detecta eventos en videos de gameplay usando heurísticas + un Vision-LLM opcional.
- Soporta muestreo configurable, análisis por LLM (Moondream2), registro de eventos con thumbnails y un camino rápido por embeddings/ANN para evitar llamadas LLM repetidas.

Requisitos mínimos
- Windows / Linux / macOS con Python 3.12 en entorno virtual (recomendado: env3.12).
- ffmpeg/ffprobe disponible (el repo incluye `./ffmpeg/bin/ffmpeg.exe` para Windows). Añade la carpeta a PATH o ajusta `config.json`.
- Dependencias Python (mínimas para desarrollo):
  - pytest (tests)
  - pillow
  - sentence-transformers (opcional, recomendado para embeddings locales)
  - annoy (opcional, fallback para ANN)
  - faiss-cpu (opcional, mejor rendimiento; conda suele ser la ruta más fácil)

Instalación (local, en venv)
1. Crear / activar venv (ejemplo PowerShell):
   ```ps
   python -m venv env3.12
   .\env3.12\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```
2. Instalar dependencias de desarrollo mínimas:
   ```ps
   python -m pip install pytest pillow
   # opcionales (mejor rendimiento):
   python -m pip install sentence-transformers annoy
   # o para faiss en conda:
   # conda install -c conda-forge faiss-cpu
   ```

Configuración
- `config.json` (opcional). Valores relevantes añadidos por la feature:
  - `sampling_rate_frames` (int) — si usas muestreo por frames
  - `sampling_mode` ("random"|"stride")
  - `sampling_stride` (int) — muestrea 1 frame cada N segundos/frames según la implementación
  - `event_registry_path` (string) — ruta base para registry (por defecto `./event_registry`)
  - `embedding_match_threshold` (float) — umbral para fast-path (por defecto 0.35)

Modo de uso (básico)
1. Aprender templates (interactive/manual/llm):
   ```ps
   python learn_templates.py "<video.mp4>" --game lol
   # Opcional: --mode manual|hybrid|llm  --sampling-stride 30
   ```
   - En modo `hybrid` intentará usar VisionLLM (si las dependencias están disponibles).
   - Para forzar que no cargue el detector real en desarrollo/tests, exporta `EVENT_CATEGORIZATION_USE_REAL=0`.

2. Registro de eventos y extracción rápida
   - La primera vez el pipeline puede descargar modelos grandes (Moondream2, sentence-transformers) si no están cacheados.
   - Para acelerar y reducir coste, el proyecto usa un camino rápido (ANN + embeddings). Instala `sentence-transformers` y `faiss-cpu`/`annoy` para producción.

Habilitar Vision LLM real
- Exporta tu token Hugging Face para mejorar descargas:
  ```ps
  setx HF_TOKEN "<your_hf_token>"
  ```
- Para desarrollo local, si no querés descargar el modelo, el wrapper por defecto actúa como stub. Para habilitar el real en tu sesión:
  ```ps
  setx EVENT_CATEGORIZATION_USE_REAL 1
  ```

Training / Registering events (--train)
-------------------------------------
You can use learn_templates.py to "train" or register events found in a video into the event registry. This is the fast path to build the event database used by the ANN fast-path.

Quick example (Windows PowerShell):
```ps
python learn_templates.py "E:\\Videos\\gameplay.mp4" --game lol --mode hybrid --train --sampling-stride 30
```

What happens when you run --train
- The learner samples frames (according to sampling_stride) and presents candidate timestamps.
- After you select a timestamp and the template is created, the pipeline will:
  - extract and save a thumbnail to ./event_registry/thumbnails/{game}/{event_id}.png
  - attempt a VisionLLM description (if enabled); otherwise use the template name as a label candidate
  - compute and persist an embedding (if sentence-transformers or OPENAI_API_KEY available)
  - check the ANN index via the fast-path; if a close match exists, attach the timestamp to the existing event instead of creating a duplicate
  - save/append the registry entry in ./event_registry/registry.json (atomic write)

Registry sample (registry.json entry)
```json
{
  "event_id": "lol_victory_1623223345",
  "label": "victory",
  "game": "lol",
  "thumbnails": ["event_registry/thumbnails/lol/lol_victory_1623223345.png"],
  "embedding_path": "event_registry/embeddings/lol_victory_1623223345.npy",
  "timestamps": [1623.34],
  "confidence": "medium",
  "created_at": "2026-06-19T14:00:00Z",
  "source": "learn_templates"
}
```

Notes and tips
- Idempotence: repeated --train on the same timestamp should not create duplicates because the fast-path and registry checks prevent obvious duplicates. If you need absolute uniqueness, enable UUID-based event_ids in config.json.
- If embedding computation fails (missing deps/API key), the entry will be created with embedding_path=null and flagged in the apply-progress logs; you can compute embeddings later and update the registry.
- To fully enable the VisionLLM analyze path set EVENT_CATEGORIZATION_USE_REAL=1 and provide HF_TOKEN in the environment.


Tests
- Ejecutar la suite de tests:
  ```ps
  py -3.12 -m pytest -q
  ```
- Notas:
  - Algunos tests simulan (mock) cargas de modelos pesadas para mantener la suite rápida.
  - Para pruebas de integración reales habilita `EVENT_CATEGORIZATION_USE_REAL=1` y asegúrate de tener HF_TOKEN y dependencias instaladas.

CLI de revisión (human-in-the-loop)
- Hay utilidades para revisar sugerencias de merge y aprobar/rechazar:
  - `python event_registry_cli.py list-suggestions --game lol --limit 10`
  - `python event_registry_cli.py review-suggestion <id> --approve` (o `--reject --merge-into <event_id>`)
  - `python event_registry_cli.py show-event <event_id>`
  - `python event_registry_cli.py export-registry --format json --out ./registry.json`

Dónde están los artefactos
- Thumbnails: `./event_registry/thumbnails/{game}/{event_id}.png`
- Embeddings: `./event_registry/embeddings/{event_id}.npy`
- Indices ANN: `./event_registry/index/{game}/...`
- Registry principal: `./event_registry/registry.json`

CI y recomendaciones
- CI debe usar Python 3.12.
- Asegurate de que ffmpeg esté disponible en runners (o mockearlo en tests). En Windows el repo incluye `./ffmpeg/bin`.
- Para rendimiento de embeddings en CI/producción instala `faiss-cpu` o `annoy`.

Cómo contribuir
- Sigue TDD estricto: cada cambio debe incluir tests (RED→GREEN→REFACTOR) y actualizar `sdd/*` artifacts cuando corresponda.
- Usa commits por work-unit y PRs encadenados (`stacked-to-main`) para cambios grandes.

Contacto
- Si algo falla, pega la traza de pytest y el archivo `sdd/event-categorization/apply-progress` (en Engram) para acelerar el diagnóstico.
