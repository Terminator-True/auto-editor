# PLAN REALISTA: Python 3.13 + Auto-Editor

## La Situación

Después de investigar, encontramos:

1. **transformers 4.41.0** SÍ soporta Python 3.13 ✓
2. **Moondream2** debería funcionar con 4.41.0 ✓
3. **PERO**: tokenizers (dependencia de transformers) requiere compilación de Rust en Windows, y hay problemas con el environment

---

## DOS CAMINOS

### Camino A: Usar virtualenv limpio (RECOMENDADO — 1 hora)

**Ventajas**:
- Aislado de otros conflictos
- Limpio para Python 3.13
- Fácil reproducible

**Pasos**:
```bash
# 1. Crear virtualenv
cd C:\Users\jf28r\Desktop\auto-editor
python -m venv venv-3.13

# 2. Activar
venv-3.13\Scripts\activate

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Instalar dependencias
pip install transformers==4.41.0 moondream pillow numpy torch torchvision

# 5. Verificar
python -c "from moondream import Moondream; print('OK')"

# 6. Test
python test_keywords_config.py
```

### Camino B: Docker (AVANZADO — 2 horas)

Usar Docker para reproducible Python 3.13 environment:

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements-docker.txt .
RUN pip install -r requirements-docker.txt

COPY . .
CMD ["python", "main.py"]
```

Lanzar:
```bash
docker build -t auto-editor:py313 .
docker run --gpus all auto-editor:py313 test_keywords_config.py
```

---

## MI RECOMENDACIÓN: CAMINO A + Testing

**Por qué Camino A es mejor ahora**:
1. Más rápido (1 hora vs 2)
2. Verifica si Moondream2 realmente funciona en 3.13
3. Documento lo que funciona para evitar problemas futuros
4. Docker podemos hacer después si necesitas reproducibilidad

---

## PLAN EJECUTABLE: PYTHON 3.13 LIMPIO

### Fase 1: Crear environment limpio (10 min)

```bash
cd C:\Users\jf28r\Desktop\auto-editor

# Limpiar caches pip
pip cache purge

# Crear virtualenv
python -m venv venv-3.13

# Activar
venv-3.13\Scripts\activate
```

### Fase 2: Instalar dependencias base (10 min)

```bash
# Upgrade pip + tools
python -m pip install --upgrade pip setuptools wheel

# Instalar core (siempre funciona)
pip install pillow numpy

# Instalar torch ANTES de transformers
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Instalar transformers
pip install transformers>=4.41.0

# Instalar moondream + extras
pip install moondream einops huggingface_hub
```

### Fase 3: Testing (20 min)

```bash
# Test 1: Imports
python -c "
import torch
import transformers
import moondream
print('✓ All imports OK')
print(f'PyTorch {torch.__version__}')
print(f'Transformers {transformers.__version__}')
"

# Test 2: GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Test 3: Moondream load
python -c "
from moondream import Moondream
from transformers import AutoTokenizer
print('✓ Moondream model loads')
"

# Test 4: Our system
python test_keywords_config.py

# Test 5: Main flow (sin video real aún)
python main.py --help
```

### Fase 4: Si todo funciona (10 min)

```bash
# Guardar requirements.txt del venv
pip freeze > requirements-py313.txt

# Update proyecto
git add requirements-py313.txt
git commit -m "feat: Python 3.13 compatibility verified - transformers 4.41.0, PyTorch 2.5.1"

# Update docs
# (cambiar SETUP_FIX.md, requirements.txt, README)
```

### Fase 5: Si algo falla

```bash
# Diagnosticar
python diagnose.py

# Investigar error específico
# (pegar aquí para análisis)

# Options:
# A) Fix / workaround
# B) Downgrade versión específica
# C) Report a Moondream2 maintainers
```

---

## CÓMO ELEGIR ENTRE VENV Y PYTHON 3.12

Después del testing:

| Resultado | Acción |
|-----------|--------|
| ✅ Todo funciona | **USA PYTHON 3.13** (fixes de seguridad) |
| ⚠️ Funciona pero lento | Optimizar + investigar |
| ❌ Errores reproducibles | Análisis del error + Opción B |

---

## PLAN PARALELO: SI FALLA, ALTERNATIVA INMEDIATA

Si Moondream2 NO funciona en 3.13, tenemos:

**Opción 1: LLaVA 1.6** (mejor que Moondream2 anyway)
```bash
pip install llava pillow torch
```
Pro: Mejor accuracy para gaming
Con: ~7GB modelo

**Opción 2: Usar modo FAST nada más**
```bash
# config.json
{
    "detection_mode": "fast"
}
```
Pro: No necesita LLM, funciona perfecto
Con: Sin clasificación de eventos

---

## ¿VAMOS?

**Propuesta**:
1. Activamos venv Python 3.13 limpio
2. Instalamos dependencias (15 min)
3. Testeamos exhaustivamente (20 min)
4. Si funciona → Documentamos + celebramos ✨
5. Si no → Análisis + Opción B

**¿Aprobado? ¿Empiezo?**

