# SOLUCIÓN RÁPIDA - Los errores que viste

## 🎯 EL PROBLEMA

Tu Python es **3.13**, pero Moondream2 solo funciona en **Python 3.10-3.12**.

Exactamente lo que dice el error:
```
[VisionLLM ERROR] Error cargando modelo: 'HfMoondream' object has no attribute 'all_tied_weights_keys'
```

Además:
- PyTorch NO está instalado (necesario para LLM)
- ffprobe no se encuentra en la ruta esperada

---

## ✅ SOLUCIÓN (30 minutos)

### Paso 1: Instala Python 3.12

1. Descarga: https://www.python.org/downloads/release/python-3120/
2. Click "Windows installer (64-bit)"
3. Instala normalmente
4. **IMPORTANTE**: Marca "Add Python 3.12 to PATH"

### Paso 2: Instala PyTorch con Python 3.12

```bash
py -3.12 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**Esto descargará ~2GB pero es una sola vez.**

### Paso 3: Instala transformers y Moondream2

```bash
py -3.12 -m pip install transformers==4.41.0 moondream einops huggingface_hub
```

### Paso 4: Instala ffmpeg globalmente

```bash
winget install Gyan.FFmpeg
```

O si no funciona:
- Descarga: https://ffmpeg.org/download.html
- Descomprime en: `C:\ffmpeg\`

### Paso 5: Verifica GPU

```bash
py -3.12 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

Debe decir: **CUDA: True**

### Paso 6: Test

```bash
cd C:\Users\jf28r\Desktop\auto-editor
py -3.12 python test_keywords_config.py
```

Debe pasar todos los tests.

### Paso 7: Ejecuta con Python 3.12

```bash
py -3.12 main.py E:\Videos\test.mp4
```

---

## ⚡ ALTERNATIVA: Modo FAST (sin LLM, ahora mismo)

Si no quieres instalar Python 3.12 ahora:

Edita `config.json`:
```json
{
    "detection_mode": "fast"
}
```

Luego:
```bash
python main.py E:\Videos\test.mp4
```

**Funciona OK pero sin LLM (sin validación de eventos).**

---

## 📝 Resumen de comandos

```bash
# Install Python 3.12 first (GUI)
# Then:

# 1. PyTorch + CUDA
py -3.12 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 2. Transformers + Moondream2
py -3.12 -m pip install transformers==4.41.0 moondream einops huggingface_hub

# 3. FFmpeg (global)
winget install Gyan.FFmpeg

# 4. Test
py -3.12 test_keywords_config.py

# 5. Run
py -3.12 main.py E:\Videos\test.mp4
```

---

## ❌ Por qué falla con Python 3.13

- Moondream2 usa `all_tied_weights_keys()` que cambió en 3.13
- PyTorch/transformers aún no fully compatible con 3.13
- Mejor aguardar a Python 3.14 o usar 3.12 por ahora

---

## 🆘 Si algo falla

Run diagnostic:
```bash
python diagnose.py
```

Pega la salida completa en tu próximo mensaje.

---

## 📚 Documentación

- `SETUP_FIX.md` — Detalles técnicos
- `requirements.txt` — Versiones exactas
- `diagnose.py` — Diagnostic script

**¿Necesitás ayuda con algo de esto?**
