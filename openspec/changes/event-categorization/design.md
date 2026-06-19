# Diseño: Mejora de prompt y pipeline en dos etapas para detección de eventos

Resumen ejecutivo
- Rediseñar el prompt entregado a Moondream2 (VisionLLM) y añadir una segunda etapa (Text-LM categorizador) que convierte descripciones visuales en etiquetas canónicas. Ajustar muestreo a 1–2 FPS con modo adaptativo para mejorar reconocimiento de palabras en pantalla y reducir falsos positivos.

Flujo de datos (ASCII)

  Video -> Muestreo (1 FPS, adaptivo) -> Frame(s)
        -> VisionLLM (descripcion_texto, score)
        -> Text-LM / Rules -> event_label (doble_kill, dragon, teamfight...)
        -> Embeddings -> ANNIndex -> fast-path match?
               │
               └─> Registry (add/update) & thumbnails

Decisiones clave

- Prompt strategy: usar prompts dirigidos que piden extracción estructurada (no yes/no) y limitar vocabulario objetivo. Razonamiento: reduces hallucinatory "sí" universal; facilita parsing.
- Two-stage design: separar percepción (VisionLLM) de clasificación (Text-LM). Razonamiento: Moondream2 es fuerte describiendo la imagen; un LLM más pequeño o reglas pueden mapear la descripción a etiquetas canónicas de forma más estable y fácil de controlar.
- Muestreo por defecto: 1 FPS. Modo 'medium' = 2 FPS, 'high' = 3 FPS. Si se detecta texto UI/plantilla o un aumento de diferencias de frame, subir temporalmente a 2–4 FPS durante ventana configurable (ej. 3s).

Prompts candidatos (español / inglés)

1) Prompt estructurado (recomendado)
- ES: "Describe en una sola frase lo que aparece claramente en este screenshot de la interfaz del juego. Sé concreto, menciona palabras visibles (p. ej. 'VICTORY', 'DOBLE KILL', 'BARON NASHOR'), los objetos importantes (dragón, torre), y evita suposiciones: devuelve solo la descripción, no conclusiones." 
- EN: "Describe in one short sentence the visible text and UI elements in this gaming screenshot. Mention visible words (e.g., 'VICTORY', 'DOUBLE KILL', 'BARON NASHOR'), key objects (dragon, tower), and avoid guessing. Return only the description."

2) Prompt checklist (extract tokens)
- ES: "Devuelve en JSON: {\"visible_text\": [..], \"ui_elements\": [..], \"notes\": \"..\"}. Extrae palabras o frases en mayúsculas y labels evidentes." 
- EN: similar JSON-structured output.

3) Prompt generativo + low-verbosity (fallback)
- ES: "Describe brevemente (3–6 palabras) lo más distintivo: ej. 'penta kill, barra roja, scoreboard'" 

Recomendación: empezar con (1) + (2) combinado: VisionLLM produce descripción libre + JSON token list. El Text-LM recibe ambos y aplica regla/embeddings.

Two-stage pipeline: interfaces y shapes

- VisionLLM.analyze_frame(image_path, prompt) -> str (description) OR JSON blob. Example shape:
  {
    "text": "Se ve la palabra VICTORY en el centro y medallas",
    "tokens": ["VICTORY"]
  }
- TextClassifier.classify_description(description:str, tokens:List[str], game:str) -> {
    "event_label": "victory" ,
    "candidates": [("victory",0.92),("teamfight",0.12)],
    "confidence": 0.92,
    "explain": "token match: VICTORY"
  }

Fallbacks y confianza
- Si VisionLLM devuelve texto vacío o muy corto, aumentar muestreo y/o marcar confidence low; el Text-LM puede apply heuristics (regex sobre tokens, e.g. 'VICTORY', 'PENTA').
- Propagar confianza: vision_confidence * text_confidence → final_confidence. Umbrales: >0.75 high, 0.5–0.75 medium, <0.5 low.

Sampling adaptativo
- Config keys: sampling_mode(str: stride|fps|adaptive), sampling_rate_fps (float), sampling_adaptive (bool), adaptive_boost_window_s (int), adaptive_trigger (template_detected|text_token_match|scene_change).
- Default: sampling_mode=fps, sampling_rate_fps=1. adaptive_boost_window_s=3.

Testing strategy
- Unit: prompt parsers, mapping rules, Text-LM classifier mapping (mock LLM outputs). 
- Integration: mock VisionLLM to produce edge-case descriptions (ambiguous, multi-label), check classifier decisions and confidence propagation. Use small fixture images.
- HIL: manual tests to review cluster suggestions and approve merges.

Backward compatibility & migración
- Añadir campo `label_canonical` y `label_version` a registry entries. Ejecutar migration script that runs Text-LM over existing descriptions to populate canonical labels (dry-run first).

Ficheros a crear/modificar
- openspec/changes/event-categorization/design.md (este documento)
- event_categorization/prompt_templates.py (store templates + helper to render with game hints)
- event_categorization/text_classifier.py (implement Text-LM wrapper + rule cascade)
- detectors/vision_llm_detector.py (ensure structured JSON output option)
- learn_templates.py (use new pipeline flow and adaptive sampling flags)
- tests/test_prompt_mapping.py, tests/test_text_classifier.py, tests/test_sampling_adaptive.py

Riesgos y mitigaciones
- Hallucination: mitigated by structured prompts + token extraction + secondary classifier.
- Cost/latency: mitigate via ANN fast-path, batching, and adaptive sampling.
- Cross-game collisions: per-game namespaces and per-game alias maps.

Próximo paso recomendado
- sdd-tasks: desglosar text_classifier + prompt_templates + tests; luego sdd-apply para implementar Text-LM and wiring.
