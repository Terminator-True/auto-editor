# SOLUCIÓN: Moondream2 + Python 3.13 + PyTorch

## 🚨 PROBLEMA IDENTIFICADO

### Error 1: `'HfMoondream' object has no attribute 'all_tied_weights_keys'`
**Causa**: Moondream2 no es compatible con la versión de `transformers` en Python 3.13

### Error 2: `ffprobe.exe no se puede encontrar`
**Causa**: Ruta relativa `.\ffmpeg\bin\ffprobe.exe` no existe (ffmpeg no instalado o en otra ruta)

---

## ✅ SOLUCIÓN PASO A PASO

### Paso 1: Verificar versiones actuales

```bash
python --version
pip list | grep -E "torch|transformers|pillow"
```

**Esperado para Moondream2**:
- Python: 3.10.x, 3.11.x, o 3.12.x (NO 3.13!)
- PyTorch: 2.0+
- Transformers: 4.35+

---

### Paso 2: OPCIÓN A - Cambiar a Python 3.12 (RECOMENDADO)

Si tienes Python 3.12 instalado:

```bash
# Listar versiones Python disponibles
py -0p

# Cambiar a Python 3.12
py -3.12 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
py -3.12 -m pip install transformers einops
```

Luego ejecutar todo con Python 3.12:
```bash
py -3.12 main.py <video.mp4>
```

---

### Paso 2: OPCIÓN B - Descargar PyTorch compatible (si solo tienes 3.13)

```bash
# Instalar PyTorch con CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Instalar transformers y dependencias
pip install transformers==4.41.0 einops pillow

# Reinstalar Moondream2 compatible
pip uninstall -y moondream
pip install moondream --upgrade
```

**Nota**: Esto puede que aún tenga problemas con Python 3.13. La mejor solución es Python 3.12.

---

### Paso 3: Verificar instalación

```bash
python -c "import torch; print('PyTorch OK:', torch.cuda.is_available())"
python -c "from transformers import AutoModelForCausalLM; print('Transformers OK')"
python -c "from PIL import Image; print('PIL OK')"
```

---

### Paso 4: Verificar ffmpeg

El error `ffprobe.exe no se puede encontrar` significa que ffmpeg no está en `.\ffmpeg\bin\`.

**Opción A**: Si lo descargaste, verifica la ruta:
```bash
ls .\ffmpeg\bin\ffprobe.exe
ls .\ffmpeg\bin\ffmpeg.exe
```

**Opción B**: Instalarlo globalmente:
```bash
# Descargar ffmpeg
# https://ffmpeg.org/download.html

# O via chocolatey
choco install ffmpeg

# O via Windows Package Manager
winget install Gyan.FFmpeg
```

Luego en `config.json`:
```json
{
    "ffmpeg_path": "ffmpeg"
}
```

---

## 🎯 RECOMENDACIÓN INMEDIATA

**Solución más rápida** (30 minutos):

1. **Downgrade a Python 3.12** (si lo tienes)
   ```bash
   py -3.12 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   py -3.12 -m pip install transformers==4.41.0 einops moondream huggingface_hub
   ```

2. **Verificar ffmpeg**
   ```bash
   python -c "import subprocess; subprocess.run(['ffprobe', '-version'])"
   ```
   Si falla, instala ffmpeg globalmente (winget install Gyan.FFmpeg)

3. **Test**
   ```bash
   py -3.12 test_keywords_config.py
   ```

---

## 🔧 WORKAROUND TEMPORAL (mientras instalas PyTorch)

Si no quieres reinstalar Python ahora, puedes usar **modo `fast`** (sin LLM):

```json
{
    "detection_mode": "fast"
}
```

Luego:
```bash
python main.py E:\Videos\test.mp4
```

**Limitaciones**:
- ✓ Detecta volumen picos
- ✓ Detecta silencio
- ✗ No usa LLM (sin validación de eventos)
- ✗ Solo templates (si los tienes configurados)

---

## 📋 CHECKLIST

- [ ] Verificar Python version: `python --version`
- [ ] Si es 3.13, instalar Python 3.12 o downgrade
- [ ] Instalar PyTorch: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`
- [ ] Instalar transformers: `pip install transformers==4.41.0`
- [ ] Instalar Moondream2: `pip install moondream huggingface_hub`
- [ ] Verificar ffmpeg: `ffmpeg -version`
- [ ] Test: `python test_keywords_config.py`
- [ ] Run: `python main.py <video.mp4>`

---

## 🆘 Si aún falla

Corre este diagnostic script:

```bash
python -c "
import sys
print(f'Python: {sys.version}')
try:
    import torch
    print(f'✓ PyTorch {torch.__version__} - GPU: {torch.cuda.is_available()}')
except:
    print('✗ PyTorch NO instalado')

try:
    from transformers import __version__
    print(f'✓ Transformers {__version__}')
except:
    print('✗ Transformers NO instalado')

try:
    from PIL import Image
    print('✓ PIL')
except:
    print('✗ PIL NO instalado')

try:
    import subprocess
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    print('✓ ffmpeg')
except:
    print('✗ ffmpeg NO disponible')
"
```

Pasa la salida en el siguiente mensaje.

