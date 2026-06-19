"""
Vision LLM Detector using Moondream2
Analyzes game frames to detect highlights, events, and context
"""

import subprocess
from pathlib import Path
import json
import re
import os

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from PIL import Image
    VISION_LLM_AVAILABLE = True
except ImportError:
    VISION_LLM_AVAILABLE = False
    print("[VisionLLM WARNING] transformers/torch no instalados. LLM Vision deshabilitado.")


class VisionLLMDetector:
    def __init__(self, ffmpeg_path="ffmpeg", model_name="vikhyatk/moondream2", device="auto", temp_dir=None, 
                 keywords_file=None, hf_token=None, config=None, game_type="generic"):
        self.ffmpeg_path = ffmpeg_path
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device = device
        self.temp_dir = Path(temp_dir) if temp_dir else Path.cwd()
        self.game_type = game_type
        
        # Keywords loading
        self.keywords = {}
        self.language = "es"  # Default
        if keywords_file:
            self._load_keywords(keywords_file)
        elif config:
            keywords_file = config.get("keywords_file")
            self.language = config.get("language", "es")
            if keywords_file:
                self._load_keywords(keywords_file)
        
        # Hugging Face token (from config, environment, or parameter)
        self.hf_token = hf_token or (config.get("hf_token") if config else None)
        if not self.hf_token:
            self.hf_token = os.environ.get("HF_TOKEN")
        
        if self.hf_token:
            print(f"[VisionLLM] ✓ Hugging Face token configurado")
        
        if not VISION_LLM_AVAILABLE:
            print("[VisionLLM ERROR] No se puede inicializar: faltan dependencias")
            return
        
        # Auto-detect device
        if device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
                print(f"[VisionLLM] GPU detectada: {torch.cuda.get_device_name(0)}")
            else:
                self.device = "cpu"
                print("[VisionLLM] Usando CPU (más lento)")
    
    def _load_keywords(self, keywords_file):
        """Load keywords from JSON file"""
        try:
            keywords_path = Path(keywords_file)
            if not keywords_path.exists():
                print(f"[VisionLLM WARNING] Keywords file not found: {keywords_file}")
                return
            
            with open(keywords_path, 'r', encoding='utf-8') as f:
                all_keywords = json.load(f)
            
            # Get language (fallback to 'es')
            language = all_keywords.get("language", self.language)
            self.language = language
            
            # Load keywords for this language and game
            if language in all_keywords:
                lang_keywords = all_keywords[language]
                
                # Load game-specific keywords
                if self.game_type in lang_keywords:
                    self.keywords = lang_keywords[self.game_type]
                    print(f"[VisionLLM] ✓ Keywords cargados ({language}/{self.game_type})")
                else:
                    # Fallback to generic
                    if "generic" in lang_keywords:
                        self.keywords = lang_keywords["generic"]
                        print(f"[VisionLLM] ✓ Keywords genéricos cargados ({language})")
            else:
                print(f"[VisionLLM WARNING] Language '{language}' not found in keywords")
        
        except Exception as e:
            print(f"[VisionLLM ERROR] Error loading keywords: {e}")
    
    def _match_keywords(self, text, event_keywords):
        """Match text against keyword list (case-insensitive)"""
        text_lower = text.lower()
        for keyword in event_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def load_model(self):
        """Load Moondream2 model (lazy loading) with HF token support"""
        if not VISION_LLM_AVAILABLE:
            print("[VisionLLM ERROR] Dependencias no disponibles (torch/transformers)")
            print("[VisionLLM ERROR] Solución: pip install torch torchvision transformers")
            return False
        
        if self.model is not None:
            return True  # Already loaded
        
        try:
            print(f"[VisionLLM] Cargando modelo {self.model_name}...")
            print("[VisionLLM] Esto puede tomar 1-2 minutos la primera vez (descarga ~2GB)")
            
            # Setup HF token for faster downloads
            if self.hf_token:
                try:
                    from huggingface_hub import login
                    login(token=self.hf_token, add_to_git_credential=False)
                    print("[VisionLLM] ✓ Autenticado con Hugging Face")
                except Exception as hf_err:
                    print(f"[VisionLLM WARNING] No se pudo autenticar con HF token: {hf_err}")
            
            # Check Python version compatibility
            import sys
            if sys.version_info >= (3, 13):
                print("[VisionLLM WARNING] Python 3.13+ detectado")
                print("[VisionLLM WARNING] Moondream2 es más estable en Python 3.10-3.12")
                print("[VisionLLM WARNING] Intentando cargar de todas formas...")
            
            # Load model with appropriate precision for GPU
            if self.device == "cuda":
                print("[VisionLLM] Usando GPU (FP16) para cargar...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    dtype=torch.float16,  # Use FP16 on GPU for speed
                    device_map="auto",
                )
            else:
                print("[VisionLLM] Usando CPU para cargar...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                )
                self.model.to(self.device)
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            print(f"[VisionLLM] ✓ Modelo cargado en {self.device}")
            return True
            
        except ImportError as e:
            print(f"[VisionLLM ERROR] Módulo faltante: {e}")
            print("[VisionLLM ERROR] Solución: pip install transformers torch torchvision")
            return False
            
        except AttributeError as e:
            print(f"[VisionLLM ERROR] Atributo no encontrado (versión incompatible): {e}")
            print("[VisionLLM ERROR] Problema: Moondream2 no es compatible con tu versión de transformers")
            print("[VisionLLM ERROR] Soluciones:")
            print("  1. Usa Python 3.10/3.11/3.12 (no 3.13+)")
            print("  2. O actualiza: pip install --upgrade transformers moondream")
            return False
        
        except Exception as e:
            print(f"[VisionLLM ERROR] Error inesperado cargando modelo: {type(e).__name__}: {e}")
            print("[VisionLLM ERROR] Detalles completos:")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_frame(self, video_path, timestamp, output_path):
        """Extract a single frame from video"""
        cmd = [
            self.ffmpeg_path,
            '-ss', str(timestamp),
            '-i', str(video_path),
            '-frames:v', '1',
            '-q:v', '2',
            '-y',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def analyze_frame(self, image_path, prompt=None):
        """
        Analyze a frame using vision LLM
        
        Args:
            image_path: Path to image file
            prompt: Custom prompt (default: gaming highlight detection in Spanish)
            
        Returns:
            str: Model response describing the frame
        """
        if not self.load_model():
            return None
        
        if prompt is None:
            # Prompt in Spanish or English depending on language config
            if self.language == "es":
                prompt = (
                    "Analiza este screenshot de un videojuego. Describe qué está pasando. "
                    "¿Es un momento emocionante (asesinato, muerte, victoria, derrota, objetivo, "
                    "multikill, pentakill, jugada épica)? Responde con el tipo de evento y descripción breve."
                )
            else:
                prompt = (
                    "Analyze this gaming screenshot. Describe what's happening. "
                    "Is this an exciting moment (kill, death, victory, defeat, objective, "
                    "multikill, pentakill, clutch play)? Answer with the event type and brief description."
                )
        
        try:
            image = Image.open(image_path)
            
            # Encode image (Moondream2 specific)
            enc_image = self.model.encode_image(image)
            
            # Generate response
            response = self.model.answer_question(enc_image, prompt, self.tokenizer)
            
            return response.strip()
            
        except Exception as e:
            print(f"[VisionLLM ERROR] Error analizando frame: {e}")
            return None
    
    def classify_highlight(self, image_path):
        """
        Classify if a frame contains a highlight-worthy moment using keywords
        
        Returns:
            dict: {
                'is_highlight': bool,
                'event_type': str,  # 'kill', 'death', 'victory', 'defeat', 'objective', 'multikill', etc.
                'confidence': str,  # 'high', 'medium', 'low'
                'description': str
            }
        """
        if self.language == "es":
            prompt = (
                "¿Es este un momento emocionante en un videojuego? "
                "Responde en JSON: "
                '{"es_highlight": verdadero/falso, "tipo_evento": "asesinato/muerte/victoria/derrota/objetivo/multikill/otro", '
                '"confianza": "alta/media/baja", "descripcion": "descripción breve"}'
            )
        else:
            prompt = (
                "Is this a highlight-worthy gaming moment? "
                "Answer in JSON format: "
                '{"is_highlight": true/false, "event_type": "kill/death/victory/defeat/objective/multikill/other", '
                '"confidence": "high/medium/low", "description": "brief description"}'
            )
        
        response = self.analyze_frame(image_path, prompt)
        
        if response is None:
            return {
                'is_highlight': False,
                'event_type': 'unknown',
                'confidence': 'low',
                'description': 'Analysis failed'
            }
        
        # Try to parse JSON response
        try:
            # Extract JSON from response (LLMs sometimes add extra text)
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                
                # Normalize keys (Spanish or English)
                if 'es_highlight' in result:
                    result['is_highlight'] = result.pop('es_highlight')
                if 'tipo_evento' in result:
                    result['event_type'] = result.pop('tipo_evento')
                if 'confianza' in result:
                    result['confidence'] = result.pop('confianza')
                if 'descripcion' in result:
                    result['description'] = result.pop('descripcion')
                
                return result
        except:
            pass
        
        # Fallback: keyword-based classification using loaded keywords
        response_lower = response.lower()
        
        # Use keywords from config if available
        if self.keywords:
            is_highlight = False
            event_type = 'other'
            
            # Check multikills first (highest priority)
            if "multikill" in self.keywords and isinstance(self.keywords["multikill"], dict):
                for multi_event, keywords_list in self.keywords["multikill"].items():
                    if self._match_keywords(response, keywords_list):
                        is_highlight = True
                        event_type = multi_event
                        break
            
            # Check other event types
            for event, keywords_list in self.keywords.items():
                if event != "multikill" and isinstance(keywords_list, list):
                    if self._match_keywords(response, keywords_list):
                        is_highlight = True
                        event_type = event
                        break
        else:
            # Fallback to hardcoded keywords (English)
            is_highlight = any(keyword in response_lower for keyword in [
                'kill', 'death', 'victory', 'defeat', 'pentakill', 'quadra', 
                'triple', 'double', 'ace', 'objective', 'baron', 'dragon', 
                'tower', 'turret', 'exciting', 'clutch', 'outplay'
            ])
            
            event_type = 'other'
            if 'victory' in response_lower or 'win' in response_lower:
                event_type = 'victory'
            elif 'defeat' in response_lower or 'loss' in response_lower:
                event_type = 'defeat'
            elif 'pentakill' in response_lower or 'penta' in response_lower:
                event_type = 'pentakill'
            elif 'quadra' in response_lower or 'quadrakill' in response_lower:
                event_type = 'quadrakill'
            elif 'triple' in response_lower:
                event_type = 'triplekill'
            elif 'double' in response_lower:
                event_type = 'doublekill'
            elif 'kill' in response_lower:
                event_type = 'kill'
            elif 'death' in response_lower or 'died' in response_lower:
                event_type = 'death'
            elif 'baron' in response_lower or 'dragon' in response_lower:
                event_type = 'objective'
        
        return {
            'is_highlight': is_highlight,
            'event_type': event_type,
            'confidence': 'medium',
            'description': response
        }
    
    def scan_video_timestamps(self, video_path, timestamps, mode='validator'):
        """
        Analyze specific timestamps in a video
        
        Args:
            video_path: Path to video
            timestamps: List of timestamps to analyze
            mode: 'validator' (classify only) or 'full' (detailed analysis)
            
        Returns:
            List of dicts with analysis results
        """
        if not self.load_model():
            print("[VisionLLM ERROR] No se pudo cargar el modelo")
            return []
        
        results = []
        temp_frame = self.temp_dir / "temp_llm_frame.png"
        
        print(f"[VisionLLM] Analizando {len(timestamps)} frames...")
        
        for i, ts in enumerate(timestamps):
            print(f"  Analizando {i+1}/{len(timestamps)} (t={ts}s)...")
            
            if not self.extract_frame(video_path, ts, temp_frame):
                print(f"    ✗ Error extrayendo frame")
                continue
            
            if mode == 'validator':
                classification = self.classify_highlight(temp_frame)
                results.append({
                    'timestamp': ts,
                    **classification
                })
                
                if classification['is_highlight']:
                    print(f"    ✓ Highlight detectado: {classification['event_type']}")
                else:
                    print(f"    − No es highlight")
            
            elif mode == 'full':
                description = self.analyze_frame(temp_frame)
                results.append({
                    'timestamp': ts,
                    'description': description
                })
                print(f"    → {description}")
        
        # Cleanup
        if temp_frame.exists():
            temp_frame.unlink()
        
        return results
    
    def is_available(self):
        """Check if vision LLM is available"""
        return VISION_LLM_AVAILABLE and self.load_model()
