"""
Vision LLM Detector using Moondream2
Analyzes game frames to detect highlights, events, and context
"""

import subprocess
from pathlib import Path
import json
import re

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from PIL import Image
    VISION_LLM_AVAILABLE = True
except ImportError:
    VISION_LLM_AVAILABLE = False
    print("[VisionLLM WARNING] transformers/torch no instalados. LLM Vision deshabilitado.")


class VisionLLMDetector:
    def __init__(self, ffmpeg_path="ffmpeg", model_name="vikhyatk/moondream2", device="auto", temp_dir=None):
        self.ffmpeg_path = ffmpeg_path
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device = device
        self.temp_dir = Path(temp_dir) if temp_dir else Path.cwd()
        
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
    
    def load_model(self):
        """Load Moondream2 model (lazy loading)"""
        if not VISION_LLM_AVAILABLE:
            print("[VisionLLM ERROR] Dependencias no disponibles")
            return False
        
        if self.model is not None:
            return True  # Already loaded
        
        try:
            print(f"[VisionLLM] Cargando modelo {self.model_name}...")
            print("[VisionLLM] Esto puede tomar 1-2 minutos la primera vez (descarga ~2GB)")
            
            # Load model with appropriate precision for GPU
            if self.device == "cuda":
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float16,  # Use FP16 on GPU for speed
                    device_map="auto"
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )
                self.model.to(self.device)
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            print(f"[VisionLLM] ✓ Modelo cargado en {self.device}")
            return True
            
        except Exception as e:
            print(f"[VisionLLM ERROR] Error cargando modelo: {e}")
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
            prompt: Custom prompt (default: gaming highlight detection)
            
        Returns:
            str: Model response describing the frame
        """
        if not self.load_model():
            return None
        
        if prompt is None:
            prompt = (
                "Analyze this gaming screenshot. Describe what's happening. "
                "Is this an exciting moment (kill, death, victory, defeat, objective, "
                "multikill, clutch play)? Answer with the event type and brief description."
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
        Classify if a frame contains a highlight-worthy moment
        
        Returns:
            dict: {
                'is_highlight': bool,
                'event_type': str,  # 'kill', 'death', 'victory', 'defeat', 'objective', 'multikill', etc.
                'confidence': str,  # 'high', 'medium', 'low'
                'description': str
            }
        """
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
                return result
        except:
            pass
        
        # Fallback: keyword-based classification
        response_lower = response.lower()
        
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
