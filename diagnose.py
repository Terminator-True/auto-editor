#!/usr/bin/env python3
"""
Diagnostic script to identify auto-editor setup issues
Run this FIRST if you're having problems
"""

import sys
import subprocess
from pathlib import Path

print("="*70)
print("AUTO-EDITOR DIAGNOSTIC SCRIPT")
print("="*70)
print()

# 1. Python version
print("[1] PYTHON VERSION")
print(f"    Version: {sys.version}")
py_minor = sys.version_info.minor
if sys.version_info.major != 3:
    print("    ✗ ERROR: Se requiere Python 3")
elif py_minor >= 13:
    print("    ⚠ WARNING: Python 3.13+ detectado")
    print("      Moondream2 puede no funcionar correctamente")
    print("      Recomendación: Usa Python 3.10/3.11/3.12")
    print("      Descarga: https://www.python.org/downloads/release/python-3120/")
elif py_minor < 10:
    print("    ⚠ WARNING: Python 3.9 o anterior")
    print("      Recomendación: Usa Python 3.10+")
else:
    print("    ✓ OK: Python 3.10-3.12 detectado")
print()

# 2. PyTorch
print("[2] PYTORCH (optional - for LLM mode)")
try:
    import torch
    print(f"    ✓ PyTorch {torch.__version__} instalado")
    print(f"    CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"    GPU: {torch.cuda.get_device_name(0)}")
        print(f"    CUDA version: {torch.version.cuda}")
    else:
        print("    ⚠ GPU no detectado (CUDA driver puede estar desactualizado)")
except ImportError:
    print("    ✗ PyTorch NO instalado (necesario para modo HYBRID/LLM)")
    print("    Solución:")
    print(f"      py -{py_minor} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
print()

# 3. Transformers
print("[3] TRANSFORMERS (optional - for LLM mode)")
try:
    from transformers import __version__
    print(f"    ✓ Transformers {__version__} instalado")
except ImportError:
    print("    ✗ Transformers NO instalado")
    print("    Solución:")
    print(f"      py -{py_minor} -m pip install transformers")
print()

# 4. Moondream2
print("[4] MOONDREAM2 (optional - for LLM mode)")
try:
    import moondream
    print(f"    ✓ Moondream2 instalado")
except ImportError:
    print("    ✗ Moondream2 NO instalado")
    print("    Solución:")
    print(f"      py -{py_minor} -m pip install moondream")
print()

# 5. PIL
print("[5] PIL/PILLOW (required)")
try:
    from PIL import Image
    print(f"    ✓ PIL instalado")
except ImportError:
    print("    ✗ PIL NO instalado")
    print("    Solución: pip install pillow")
print()

# 6. NumPy
print("[6] NUMPY (required)")
try:
    import numpy
    print(f"    ✓ NumPy {numpy.__version__} instalado")
except ImportError:
    print("    ✗ NumPy NO instalado")
    print("    Solución: pip install numpy")
print()

# 7. FFmpeg
print("[7] FFMPEG (required)")
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=2)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0]
        print(f"    ✓ ffmpeg detectado: {version_line}")
    else:
        print("    ✗ ffmpeg no funciona correctamente")
except FileNotFoundError:
    print("    ✗ ffmpeg NO encontrado en PATH")
    print("    Solución:")
    print("      winget install Gyan.FFmpeg")
    print("      O descargar: https://ffmpeg.org/download.html")
except subprocess.TimeoutExpired:
    print("    ⚠ ffmpeg timeout (puede estar funcionando, intenta manualmente)")
except Exception as e:
    print(f"    ✗ Error verificando ffmpeg: {e}")
print()

# 8. FFprobe
print("[8] FFPROBE (required)")
try:
    result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=2)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0]
        print(f"    ✓ ffprobe detectado: {version_line}")
    else:
        print("    ✗ ffprobe no funciona correctamente")
except FileNotFoundError:
    print("    ✗ ffprobe NO encontrado en PATH")
    print("    Nota: Viene con ffmpeg, verifica instalación")
except Exception as e:
    print(f"    ✗ Error verificando ffprobe: {e}")
print()

# 9. Config files
print("[9] ARCHIVOS DE CONFIGURACION")
config_path = Path("config.json")
keywords_path = Path("keywords.json")

if config_path.exists():
    print(f"    ✓ config.json existe")
    try:
        import json
        with open(config_path) as f:
            config = json.load(f)
        print(f"      - detection_mode: {config.get('detection_mode', 'N/A')}")
        print(f"      - game_type: {config.get('game_type', 'N/A')}")
        print(f"      - ffmpeg_path: {config.get('ffmpeg_path', 'N/A')}")
    except Exception as e:
        print(f"    ✗ Error leyendo config.json: {e}")
else:
    print(f"    ✗ config.json NO existe")

if keywords_path.exists():
    print(f"    ✓ keywords.json existe")
else:
    print(f"    ✗ keywords.json NO existe")
print()

# 10. Summary
print("="*70)
print("RESUMEN Y RECOMENDACIONES")
print("="*70)

required_ok = all([
    Path("config.json").exists(),
    Path("keywords.json").exists()
])

try:
    import PIL, numpy
    required_ok = required_ok and True
except:
    required_ok = False

try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=1, check=True)
    subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=1, check=True)
except:
    required_ok = False

if required_ok:
    print("✓ Modo FAST (sin LLM) debería funcionar")
else:
    print("✗ Hay problemas que impiden cualquier modo")
    print("  Instala las dependencias básicas primero")
    print("  pip install pillow numpy")
    print("  Luego: winget install Gyan.FFmpeg")

try:
    import torch
    from transformers import __version__
    import moondream
    
    if sys.version_info >= (3, 13):
        print("⚠ Modo HYBRID/LLM requiere Python 3.12 (tienes 3.13+)")
        print("  Solución: Descarga Python 3.12 y ejecuta con: py -3.12 main.py")
    else:
        print("✓ Modo HYBRID/LLM debería funcionar")
except:
    print("⚠ Modo HYBRID/LLM no disponible (falta pytorch/transformers/moondream)")
    print("  Instala:")
    print(f"    py -{py_minor} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
    print(f"    py -{py_minor} -m pip install transformers moondream einops")

print()
print("Para más ayuda, revisa SETUP_FIX.md")
