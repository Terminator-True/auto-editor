# Quick Reference — Keywords + Hugging Face Token

## 🌍 Keywords JSON

Sistema multi-idioma para detección de eventos. Organización:

```
keywords.json
├── language: "es" (idioma por defecto)
├── es (español)
│   ├── lol
│   │   ├── multikill (pentakill, quadra, triple, double)
│   │   ├── victory
│   │   ├── defeat
│   │   ├── kill
│   │   ├── death
│   │   ├── objective (barón, dragón, torre)
│   │   └── clutch
│   ├── valorant
│   └── generic
└── en (inglés)
    └── (misma estructura)
```

### Cómo agregar palabras clave

**Ejemplo**: Querés agregar "¡ult ganada!" como victoria en LoL español

```json
"es": {
    "lol": {
        "victory": [
            "victoria",
            "ganaste",
            "equipo ganador",
            "¡ult ganada!",  ← NUEVA
            "equipo lol ganador"
        ]
    }
}
```

El detector verificará si la respuesta del LLM contiene **cualquiera** de estas palabras.

### Cómo agregar un nuevo juego

```json
"es": {
    "minecraft": {
        "victory": ["destruiste dragón", "dragón del fin eliminado"],
        "death": ["moriste", "fuiste asesinado"],
        "kill": ["enemigo muerto", "mob eliminado"]
    }
}
```

Luego en `config.json`:
```json
{
    "game_type": "minecraft",
    "language": "es"
}
```

---

## 🔑 Hugging Face Token

Opcionalmente acelera descargas del modelo Moondream2 (~2GB):

### Obtener token

1. https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Name: "auto-editor" (opcional)
4. Role: **Read** (no necesita Write)
5. Copy token

### Usar token

**Opción A**: `config.json` (persistente)
```json
{
    "hf_token": "hf_abcd1234efgh5678ijkl9012"
}
```

**Opción B**: Variable de entorno (seguro)
```bash
# PowerShell
$env:HF_TOKEN = "hf_abcd1234efgh5678ijkl9012"
python main.py video.mp4

# CMD
set HF_TOKEN=hf_abcd1234efgh5678ijkl9012
python main.py video.mp4
```

**Opción C**: Ambas (env sobrescribe config.json)

---

## ⚙️ config.json — Campos nuevos

```json
{
    "language": "es",
    "keywords_file": "./keywords.json",
    "hf_token": null
}
```

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `language` | Idioma para keywords + LLM prompts | `"es"` o `"en"` |
| `keywords_file` | Ruta a keywords.json | `"./keywords.json"` o `"C:\\Keywords\\es.json"` |
| `hf_token` | Token de Hugging Face (opcional) | `"hf_..."` o `null` |

---

## 🔄 Flujo de detección con keywords

1. **LLM analiza frame** → "¡Pentakill en LoL, equipo ganador!"
2. **classify_highlight() llama keywords** → busca en `config.json["language"]` + `config.json["game_type"]`
3. **Coincide contra keywords.json** → "pentakill" ✓ y "victoria" ✓
4. **Resultado**: `event_type = "pentakill"`, `is_highlight = true`

Sin keywords (fallback inglés hardcoded):
- ❌ "¡Pentakill en LoL!" → No detecta (busca "pentakill" nada más)

---

## 💡 Tips

**Para máxima precisión en español**:
```json
{
    "language": "es",
    "detection_mode": "hybrid",
    "game_type": "lol",
    "hf_token": "hf_..."
}
```

**Si no tienes token de HF**:
- Primera run: ~5 min para descargar Moondream2 la primera vez
- Siguientes: instantáneo (usa caché local)
- Sin token: posible que tarde más si estás compartiendo bandwidth

**Para agregar tu propio juego**:
1. Edita `keywords.json`
2. Agrega estructura `"es": { "mi_juego": { "event_type": [...] } }`
3. En `config.json`: `"game_type": "mi_juego"`
4. Listo, no necesita recompilar

---

## 📚 Referencia rápida

| Tarea | Comando |
|------|---------|
| Usar keywords en español | `"language": "es"` en config.json |
| Usar keywords en inglés | `"language": "en"` en config.json |
| Agregar token HF | `"hf_token": "hf_..."` en config.json |
| Ver token configurado | Chequea config.json o `$env:HF_TOKEN` |
| Override temporal | `python main.py video.mp4` (usa config.json) |
| Test LLM sin tokens | Modo `fast` (no usa LLM, no necesita token) |
