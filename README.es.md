# auto-editor — Extracción de eventos y plantillas

Resumen corto
- auto-editor extrae plantillas y clasifica eventos en videos de gameplay usando heurísticas y una IA de visión opcional.

Uso rápido
- Activar entorno virtual (env3.12) y asegurarse de tener ffmpeg disponible.
- Ejecutar para aprender templates:
  ```ps
  python learn_templates.py "<video.mp4>" --game lol --mode hybrid
  ```

Registro / Entrenamiento

- Para registrar eventos detectados (thumbnails, embeddings, registry.json) usá --train o --register:

  python learn_templates.py "<video.mp4>" --game generic --train

La ubicación del registro puede sobrescribirse con la variable de entorno EVENT_REGISTRY_BASE.

Pruebas
- Ejecutar la suite de tests con:
  ```ps
  py -3.12 -m pytest -q
  ```

Notas importantes
- Para rendimiento de embeddings instala `sentence-transformers` y `faiss-cpu` o `annoy`.
- El wrapper de VisionLLM usa un stub por defecto; activa el real con:
  ```ps
  setx EVENT_CATEGORIZATION_USE_REAL 1
  ```

Más detalles en README.md (inglés).
