# Auto-Template Learning System

Script automatizado para generar templates a partir de un video de referencia.

## 🎯 Propósito

En lugar de crear templates manualmente, usá un video de referencia para que el sistema aprenda automáticamente:
- Victory/Defeat screens
- UI elements específicos del juego
- Regiones normalizadas optimizadas

**Una sola vez por juego** → Templates listos para todos los videos futuros.

---

## 🚀 Uso Rápido

### Paso 1: Grabar video de referencia

Jugá UNA partida completa de tu juego favorito. Asegurate de que incluya:
- ✅ Pantalla de Victoria O Derrota
- ✅ Momentos variados (early, mid, late game)
- ✅ UI completa visible

**Ejemplo**: Una partida de LoL de 30-40 minutos.

### Paso 2: Ejecutar learning script

```bash
python learn_templates.py D:\lol_reference.mp4 --game lol
```

### Paso 3: Revisar y confirmar

El script:
1. Escanea el video con LLM (RTX 3060)
2. Encuentra candidatos automáticamente
3. Te muestra las opciones
4. Vos confirmás la mejor
5. Genera templates + config automáticamente

---

## 📋 Workflow Detallado

### Ejemplo: League of Legends

```bash
python learn_templates.py D:\lol_reference.mp4 --game lol
```

**Output del script**:

```
======================================================================
AUTO-TEMPLATE LEARNER
Video: D:\lol_reference.mp4
Game: lol
Mode: hybrid
======================================================================

[INFO] Resolución del video: 2560x1080

======================================================================
DETECTANDO: VICTORY
======================================================================

[INFO] Escaneando video en busca de: victory
[INFO] Esto puede tomar varios minutos...
  Analizando frame 45/60 (t=900.0s)...
  ✓ Posible victory detectado en 920.5s

[INFO] Encontrados 1 candidatos para victory

[INFO] Mostrando candidatos para victory...
[INFO] Los frames se guardarán en ./candidates/ para que los revises
  1. t=920.5s → victory_1_920.png

[INFO] Revisa las imágenes en ./candidates/
[INFO] ¿Cuál es el mejor victory? (1-1, 0 para ninguno)
Selección: 1

[SUCCESS] ✓ Seleccionado: t=920.5s

[INFO] Creando template: lol_victory
[INFO] Usando región normalizada: (0.395, 0.278, 0.208, 0.185)
[INFO] Equivalente en píxeles: (1011, 300, 532, 199)
[TemplateDetector] ✓ Template 'lol_victory' creado: templates/lol_victory.png

======================================================================
DETECTANDO: DEFEAT
======================================================================

[INFO] Escaneando video en busca de: defeat
[INFO] Esto puede tomar varios minutos...
  (si no hay defeat en este video, no encontrará ninguno)

[INFO] Encontrados 0 candidatos para defeat
[WARNING] No se encontraron candidatos para defeat

======================================================================
CONFIGURACIÓN GENERADA
======================================================================

Agrega esto a tu config.json:

{
  "template_regions": {
    "lol_victory": [0.395, 0.278, 0.208, 0.185]
  }
}

[SUCCESS] ✓ Guardado en: config_snippet_lol.json
======================================================================

[SUCCESS] ✓ Templates generados exitosamente
[SUCCESS] ✓ Total: 1 templates

Próximos pasos:
1. Revisa los templates en ./templates/
2. Copia el snippet a config.json
3. Prueba con: python main.py <video>.mp4
```

---

## ⚙️ Modos de Operación

### Modo Hybrid (RECOMENDADO)

```bash
python learn_templates.py video.mp4 --game lol --mode hybrid
```

**Cómo funciona**:
1. LLM escanea automáticamente (aprovecha tu RTX 3060)
2. Encuentra candidatos probables
3. Te muestra opciones para confirmar
4. Genera templates con las mejores opciones

**Ventajas**:
- Rápido (LLM hace el trabajo pesado)
- Preciso (vos confirmas)
- Aprende de tus decisiones

### Modo LLM-Only

```bash
python learn_templates.py video.mp4 --game lol --mode llm
```

**Cómo funciona**:
1. LLM escanea y decide automáticamente
2. No pide confirmación
3. Genera templates con alta confianza

**Ventajas**:
- Completamente automático
- Útil si tenés muchos juegos que aprender

**Contras**:
- Puede generar falsos positivos

### Modo Manual

```bash
python learn_templates.py video.mp4 --game lol --mode manual
```

**Cómo funciona**:
1. Detecta cambios visuales bruscos
2. Te muestra frames candidatos
3. Vos decidís cuál es cada evento

**Ventajas**:
- No requiere LLM (funciona sin GPU)

**Contras**:
- Más lento (revisión manual)

---

## 🎮 Juegos Soportados

### League of Legends

```bash
python learn_templates.py lol.mp4 --game lol
```

**Detecta**:
- Victory screen (pantalla azul "VICTORIA")
- Defeat screen (pantalla roja "DERROTA")

**Región óptima**: Centro-superior (0.395, 0.278, 0.208, 0.185)

### Valorant

```bash
python learn_templates.py valorant.mp4 --game valorant
```

**Detecta**:
- Victory screen (round win)
- ACE notification

**Región óptima**: Top-center (0.42, 0.1, 0.16, 0.08)

### Genérico

```bash
python learn_templates.py gameplay.mp4 --game generic
```

**Detecta**:
- Victory/Win screens (genérico)
- Defeat/Loss screens (genérico)

**Región óptima**: Centro 50% (0.25, 0.25, 0.5, 0.5)

---

## 📂 Archivos Generados

Después de ejecutar el script:

```
auto-editor/
├── templates/
│   ├── lol_victory.png          # ✅ Template creado
│   └── lol_defeat.png            # ✅ Template creado (si hubo defeat)
├── candidates/
│   ├── victory_1_920.png         # Frame candidato (para revisar)
│   └── defeat_1_1500.png         # Frame candidato
└── config_snippet_lol.json       # ✅ Snippet para config.json
```

---

## 🔧 Configuración Post-Learning

### Paso 1: Copiar snippet a config.json

Abrí `config_snippet_lol.json`:

```json
{
  "template_regions": {
    "lol_victory": [0.395, 0.278, 0.208, 0.185],
    "lol_defeat": [0.395, 0.278, 0.208, 0.185]
  }
}
```

Pegá en tu `config.json`:

```json
{
    "ffmpeg_path": "...",
    "detection_mode": "hybrid",
    "game_type": "lol",
    
    "template_regions": {
        "lol_victory": [0.395, 0.278, 0.208, 0.185],
        "lol_defeat": [0.395, 0.278, 0.208, 0.185]
    },
    
    "enable_template_detection": true
}
```

### Paso 2: Verificar templates

Revisá que los PNG se vean bien:

```
templates/lol_victory.png  ← Debe mostrar "VICTORIA" claramente
templates/lol_defeat.png   ← Debe mostrar "DERROTA" claramente
```

### Paso 3: Probar

```bash
python main.py D:\nuevo_gameplay.mp4
```

Debería detectar Victory/Defeat automáticamente.

---

## 💡 Tips y Mejores Prácticas

### Elegir video de referencia

✅ **BUENO**:
- Partida completa de principio a fin
- Incluye Victoria O Derrota (idealmente ambas, pero con una alcanza)
- UI completa visible (no modo espectador)
- Resolución nativa de tu setup

❌ **MALO**:
- Solo highlights cortos
- UI oculta
- Resolución distinta a la que usás normalmente
- Stream de Twitch (puede tener overlays)

### Scaneo eficiente

Para videos largos (1h+), reducí el intervalo al final:

```bash
# Video de 2 horas, probablemente Victory/Defeat está en los últimos 30 min
# Modificar el script o usar --scan-start y --scan-end (feature futuro)
```

### Multiple games

Creá un snippet por juego:

```bash
python learn_templates.py lol.mp4 --game lol
python learn_templates.py valorant.mp4 --game valorant
python learn_templates.py csgo.mp4 --game csgo
```

Después combiná todos en config.json:

```json
{
    "template_regions": {
        "lol_victory": [...],
        "lol_defeat": [...],
        "valorant_victory": [...],
        "valorant_ace": [...],
        "csgo_round_win": [...]
    }
}
```

---

## 🐛 Troubleshooting

### "No se encontraron candidatos"

**Causa**: El video no tiene el evento buscado (ej: solo hay Victory, no Defeat)

**Solución**:
- Normal si solo ganaste (o perdiste)
- Grabar otro video con el evento faltante
- O usar template genérico

### LLM muy lento

**Causa**: Intervalo de escaneo muy bajo

**Solución**:
- El script usa 20s por defecto (balance velocidad/precisión)
- Para videos MUY largos, aumentar manualmente en el código: `scan_interval=30`

### Candidatos incorrectos

**Causa**: LLM detectó frame similar pero no correcto

**Solución**:
- Revisar ./candidates/ ANTES de confirmar
- Elegir el mejor candidato manualmente
- Si ninguno es bueno, seleccionar 0 (ninguno)

### Templates se ven mal

**Causa**: Región automática no es óptima para tu juego

**Solución**:
- Usar `create_template.py` manualmente con región custom:
  ```bash
  python create_template.py video.mp4 920 lol_victory --norm 0.4 0.3 0.2 0.15
  ```

---

## 🔮 Roadmap (Features Futuras)

- [ ] `--scan-start` y `--scan-end` para limitar escaneo temporal
- [ ] `--interactive-crop` para ajustar región manualmente
- [ ] Detección automática de región óptima con computer vision
- [ ] Soporte para más juegos (CS:GO, Overwatch, Fortnite)
- [ ] Batch learning (múltiples videos a la vez)
- [ ] Fine-tuning de threshold automático

---

## 📊 Comparación: Manual vs Auto-Learning

| Aspecto | Manual (create_template.py) | Auto-Learning |
|---------|----------------------------|---------------|
| **Tiempo** | ~10 min por template | ~5-10 min para TODO el juego |
| **Precisión** | 100% (vos decidís) | ~95% (LLM + confirmación) |
| **Escalabilidad** | Bajo (1 template a la vez) | Alto (todos los eventos juntos) |
| **Requiere conocimiento** | Sí (timestamps exactos) | No (detecta automáticamente) |
| **Regiones normalizadas** | Manual | Automático |
| **Config.json** | Copiar manualmente | Generado automáticamente |

---

## 📝 Ejemplo Completo: Workflow End-to-End

### Día 1: Learning (una sola vez)

```bash
# 1. Grabar partida de LoL completa
# OBS → D:\videos\lol_reference.mp4

# 2. Ejecutar learning
python learn_templates.py D:\videos\lol_reference.mp4 --game lol

# 3. Revisar candidatos en ./candidates/
# 4. Confirmar mejores opciones
# 5. Copiar snippet a config.json
```

### Día 2-365: Uso normal

```bash
# Procesar cualquier gameplay futuro:
python main.py D:\videos\lol_2025-01-16.mp4
python main.py D:\videos\lol_2025-01-17.mp4
python main.py D:\videos\lol_2025-01-18.mp4

# Templates ya aprendidos → detección automática ✅
```

---

**¿Preguntas?** Abrí un issue o revisá el README principal.
