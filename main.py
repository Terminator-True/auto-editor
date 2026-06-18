import os
import sys
import json
import subprocess
from pathlib import Path

# Import detection modules
from detectors import SilenceDetector, TemplateDetector, VisionLLMDetector


class HybridVideoProcessor:
    """
    Hybrid multi-modal video processor for gaming highlights
    
    Supports 3 detection modes:
    - fast: Template matching + audio analysis only
    - hybrid: Fast track + LLM validation
    - llm_only: Full LLM vision analysis
    """
    
    def __init__(self, video_path, config=None):
        self.video_path = video_path
        self.video_name = Path(video_path).stem
        self.video_dir = Path(video_path).parent
        
        # Load config (can be dict or path)
        if isinstance(config, dict):
            self.config = config
        elif isinstance(config, str):
            self.config = self.load_config(config)
        else:
            self.config = {}
        
        self.ffmpeg_path = self.config.get("ffmpeg_path", "ffmpeg")
        
        # Directories configuration
        self.timestamps_file = self.video_dir / f"{self.video_name}_timestamps.json"
        
        # Output directory (configurable)
        output_dir_config = self.config.get("output_directory")
        if output_dir_config:
            self.output_dir = Path(output_dir_config)
        else:
            self.output_dir = self.video_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Temp directory (configurable)
        temp_dir_config = self.config.get("temp_directory")
        if temp_dir_config:
            self.temp_dir = Path(temp_dir_config)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = None  # Use default system temp
        
        print(f"[INFO] Output directory: {self.output_dir}")
        if self.temp_dir:
            print(f"[INFO] Temp directory: {self.temp_dir}")
        
        # Detection mode
        self.detection_mode = self.config.get("detection_mode", "hybrid")
        
        # Initialize detectors
        self.silence_detector = SilenceDetector(self.ffmpeg_path)
        self.template_detector = TemplateDetector(self.ffmpeg_path, temp_dir=self.temp_dir)
        self.vision_llm = None
        
        # Initialize LLM if needed
        if self.detection_mode in ['hybrid', 'llm_only']:
            self.vision_llm = VisionLLMDetector(self.ffmpeg_path, temp_dir=self.temp_dir)
            self.vision_llm = VisionLLMDetector(self.ffmpeg_path)
        
        print(f"[INFO] Modo de detección: {self.detection_mode}")
    
    def load_config(self, config_path):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] No se pudo cargar config.json: {e}")
            return {}
    
    def load_manual_timestamps(self):
        """Load timestamps from OBS marker script"""
        if not self.timestamps_file.exists():
            print(f"[WARNING] No se encontró {self.timestamps_file}")
            return []
        
        try:
            with open(self.timestamps_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[INFO] Cargados {len(data)} marcadores manuales de OBS")
                return data
        except Exception as e:
            print(f"[ERROR] Error leyendo timestamps: {e}")
            return []
    
    def detect_volume_peaks(self):
        """Detect loud moments using silence detector"""
        if not self.config.get("enable_auto_detection", True):
            return []
        
        print("[INFO] Detectando picos de volumen...")
        silence_periods = self.silence_detector.detect_silence_periods(
            self.video_path,
            noise_threshold=self.config.get("volume_threshold", -20),
            min_duration=self.config.get("min_peak_duration", 2)
        )
        
        # Convert silence periods to loud timestamps (ends of silence)
        loud_timestamps = []
        for silence_start, silence_end in silence_periods:
            loud_timestamps.append({
                "time": silence_end,
                "type": "auto_volume",
                "duration": self.config.get("auto_clip_duration", 30),
                "confidence": "medium"
            })
        
        print(f"[INFO] Detectados {len(loud_timestamps)} picos de volumen")
        return loud_timestamps
    
    def detect_template_events(self):
        """Detect game-specific events using template matching"""
        if self.detection_mode == 'llm_only':
            return []
        
        if not self.config.get("enable_template_detection", True):
            return []
        
        game_type = self.config.get("game_type", "generic")
        
        if game_type == "lol":
            return self._detect_lol_events()
        
        # Add other games here
        return []
    
    def _detect_lol_events(self):
        """Detect League of Legends specific events"""
        print("[INFO] Detectando eventos de League of Legends...")
        
        events = []
        
        # Get template regions from config (normalized coordinates)
        template_regions = self.config.get("template_regions", {})
        
        # Detect Victory screen
        victory_region = template_regions.get("lol_victory")
        victory_matches = self.template_detector.scan_video(
            self.video_path,
            template_name="lol_victory",
            interval=10,
            threshold=self.config.get("template_threshold", 75),
            region=victory_region,
            normalized=True if victory_region else False
        )
        
        for ts in victory_matches:
            events.append({
                "time": ts,
                "type": "victory",
                "duration": 10,
                "confidence": "high"
            })
        
        # Detect Defeat screen
        defeat_region = template_regions.get("lol_defeat")
        defeat_matches = self.template_detector.scan_video(
            self.video_path,
            template_name="lol_defeat",
            interval=10,
            threshold=self.config.get("template_threshold", 75),
            region=defeat_region,
            normalized=True if defeat_region else False
        )
        
        for ts in defeat_matches:
            events.append({
                "time": ts,
                "type": "defeat",
                "duration": 10,
                "confidence": "high"
            })
        
        print(f"[INFO] Detectados {len(events)} eventos de LoL (template matching)")
        return events
    
    def validate_with_llm(self, timestamps):
        """Validate timestamps using vision LLM"""
        if self.vision_llm is None or not self.vision_llm.is_available():
            print("[WARNING] LLM Vision no disponible, saltando validación")
            return timestamps
        
        print("[INFO] Validando timestamps con LLM Vision...")
        
        # Analyze timestamps
        llm_results = self.vision_llm.scan_video_timestamps(
            self.video_path,
            [ts['time'] for ts in timestamps],
            mode='validator'
        )
        
        # Merge results
        validated = []
        for i, ts in enumerate(timestamps):
            if i < len(llm_results):
                llm_result = llm_results[i]
                
                # Update timestamp with LLM insights
                if llm_result['is_highlight']:
                    ts['llm_validated'] = True
                    ts['llm_event_type'] = llm_result['event_type']
                    ts['llm_confidence'] = llm_result['confidence']
                    ts['llm_description'] = llm_result['description']
                    validated.append(ts)
                else:
                    # LLM says it's not a highlight - skip if confidence is high
                    if llm_result['confidence'] == 'high':
                        print(f"  ✗ Rechazado por LLM: {ts['time']}s")
                    else:
                        # Keep it anyway if LLM is uncertain
                        validated.append(ts)
            else:
                validated.append(ts)
        
        print(f"[INFO] LLM validó {len(validated)}/{len(timestamps)} timestamps")
        return validated
    
    def analyze_with_llm_only(self):
        """Full LLM analysis mode (no fast track)"""
        if self.vision_llm is None or not self.vision_llm.is_available():
            print("[ERROR] LLM Vision no disponible")
            return []
        
        print("[INFO] Modo LLM puro: analizando video completo...")
        
        # Get video duration
        duration = self._get_video_duration()
        if duration is None:
            return []
        
        # Sample frames at intervals
        interval = self.config.get("llm_scan_interval", 30)  # Every 30 seconds
        
        timestamps_to_analyze = []
        t = 0
        while t < duration:
            timestamps_to_analyze.append(t)
            t += interval
        
        # Analyze all timestamps
        llm_results = self.vision_llm.scan_video_timestamps(
            self.video_path,
            timestamps_to_analyze,
            mode='validator'
        )
        
        # Convert to timestamp format
        highlights = []
        for result in llm_results:
            if result['is_highlight']:
                highlights.append({
                    "time": result['timestamp'],
                    "type": result['event_type'],
                    "duration": self.config.get("default_clip_duration", 60),
                    "confidence": result['confidence'],
                    "description": result['description'],
                    "llm_validated": True
                })
        
        print(f"[INFO] LLM encontró {len(highlights)} highlights")
        return highlights
    
    def merge_timestamps(self, manual, auto, template_events):
        """Merge manual, auto-detected, and template-detected timestamps"""
        all_timestamps = manual + auto + template_events
        
        # Sort by time
        all_timestamps.sort(key=lambda x: x['time'])
        
        # Remove duplicates (within min_gap)
        min_gap = self.config.get("min_clip_gap", 30)
        filtered = []
        
        for ts in all_timestamps:
            if not filtered or (ts['time'] - filtered[-1]['time']) >= min_gap:
                filtered.append(ts)
            else:
                # Prioritize: manual > template > auto
                current = filtered[-1]
                priority_order = ['highlight', 'partida_start', 'partida_end', 'victory', 'defeat', 'auto_volume']
                
                current_priority = priority_order.index(current['type']) if current['type'] in priority_order else 999
                new_priority = priority_order.index(ts['type']) if ts['type'] in priority_order else 999
                
                if new_priority < current_priority:
                    filtered[-1] = ts
        
        print(f"[INFO] Merged timestamps: {len(all_timestamps)} → {len(filtered)} (después de filtrado)")
        return filtered
    
    def _get_video_duration(self):
        """Get video duration using ffprobe"""
        cmd = [
            self.ffmpeg_path.replace('ffmpeg', 'ffprobe'),
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(self.video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            print(f"[ERROR] No se pudo obtener duración: {e}")
            return None
    
    def cut_clip(self, timestamp, duration, output_path):
        """Cut a single clip using ffmpeg -c copy (no re-encoding)"""
        start_time = max(0, timestamp - duration / 2)
        
        cmd = [
            self.ffmpeg_path,
            '-ss', str(start_time),
            '-i', self.video_path,
            '-t', str(duration),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-y',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Error cortando clip: {e}")
            return False
    
    def compile_final_video(self, clip_paths, output_name="highlights_final.mp4"):
        """Compile all clips into a single video using ffmpeg concat"""
        if not clip_paths:
            print("[WARNING] No hay clips para compilar")
            return None
        
        # Create concat file
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, 'w', encoding='utf-8') as f:
            for clip in clip_paths:
                abs_path = Path(clip).resolve()
                f.write(f"file '{abs_path}'\n")
        
        output_path = self.output_dir / output_name
        
        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            '-y',
            str(output_path)
        ]
        
        try:
            print(f"[INFO] Compilando {len(clip_paths)} clips en video final...")
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[SUCCESS] ✓ Video final creado: {output_path}")
            
            # Clean up concat file
            concat_file.unlink()
            
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Error compilando video final: {e}")
            return None
    
    def remove_silence_from_final(self, input_video):
        """Remove silence from final compiled video"""
        if not self.config.get("remove_silence", False):
            return input_video
        
        print("[INFO] Eliminando silencios del video final...")
        
        output_path = self.output_dir / f"{input_video.stem}_nosilence{input_video.suffix}"
        
        success = self.silence_detector.remove_silence(
            input_video,
            output_path,
            noise_threshold=self.config.get("silence_threshold", -40),
            min_duration=self.config.get("min_silence_duration", 2)
        )
        
        if success:
            return output_path
        else:
            return input_video
    
    def process(self):
        """Main processing pipeline"""
        print("=" * 70)
        print(f"[INFO] Auto-Editor v2.0 - Hybrid Mode")
        print(f"[INFO] Video: {self.video_path}")
        print(f"[INFO] Modo: {self.detection_mode}")
        print("=" * 70)
        
        # Step 1: Load manual timestamps from OBS
        manual_timestamps = self.load_manual_timestamps()
        
        all_timestamps = []
        
        if self.detection_mode == 'llm_only':
            # Full LLM analysis
            all_timestamps = self.analyze_with_llm_only()
            
            # Still merge with manual markers
            all_timestamps = self.merge_timestamps(manual_timestamps, all_timestamps, [])
        
        else:
            # Fast track: volume + templates
            auto_timestamps = self.detect_volume_peaks()
            template_events = self.detect_template_events()
            
            # Merge all sources
            all_timestamps = self.merge_timestamps(manual_timestamps, auto_timestamps, template_events)
            
            # Validate with LLM if hybrid mode
            if self.detection_mode == 'hybrid' and self.vision_llm:
                all_timestamps = self.validate_with_llm(all_timestamps)
        
        if not all_timestamps:
            print("[WARNING] No se encontraron momentos para procesar")
            return
        
        # Step 2: Cut clips
        print(f"\n[INFO] Cortando {len(all_timestamps)} clips...")
        clip_paths = []
        
        for i, ts in enumerate(all_timestamps):
            duration = ts.get('duration', self.config.get('default_clip_duration', 60))
            clip_type = ts.get('type', 'clip')
            
            # Add LLM label if available
            label = clip_type
            if ts.get('llm_event_type'):
                label = ts['llm_event_type']
            
            output_path = self.output_dir / f"{i+1:03d}_{label}_{int(ts['time'])}.mp4"
            
            if self.cut_clip(ts['time'], duration, output_path):
                clip_paths.append(output_path)
                
                description = ts.get('llm_description', '')
                confidence = ts.get('confidence', 'unknown')
                print(f"  ✓ Clip {i+1}/{len(all_timestamps)}: {output_path.name} ({confidence}) {description}")
        
        # Step 3: Compile final video
        if clip_paths:
            print(f"\n[INFO] Total clips cortados: {len(clip_paths)}")
            final_video = self.compile_final_video(clip_paths)
            
            if final_video:
                # Optional: Remove silence from final video
                final_video = self.remove_silence_from_final(final_video)
                
                print("\n" + "=" * 70)
                print(f"[SUCCESS] ✓ Proceso completado exitosamente")
                print(f"[SUCCESS] Video final: {final_video}")
                print(f"[SUCCESS] Clips individuales: {self.output_dir}")
                print("=" * 70)
            
            # Cleanup individual clips if configured
            if not self.config.get("keep_individual_clips", True):
                print("\n[INFO] Eliminando clips individuales...")
                for clip in clip_paths:
                    try:
                        Path(clip).unlink()
                    except:
                        pass


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auto-Editor v2.0 - Hybrid Multi-Modal Video Highlight Detector',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Básico (output en misma carpeta que el video):
  python main.py D:\\gameplay.mp4
  
  # Con directorio de output custom:
  python main.py D:\\gameplay.mp4 --output E:\\highlights
  
  # Con directorio temporal custom (para archivos intermedios):
  python main.py D:\\gameplay.mp4 --output E:\\highlights --temp E:\\temp
  
  # Con config custom:
  python main.py D:\\gameplay.mp4 --config my_config.json
        """
    )
    
    parser.add_argument('video', help='Archivo de video a procesar')
    parser.add_argument('-o', '--output', help='Directorio de salida para clips y video final')
    parser.add_argument('-t', '--temp', help='Directorio temporal para archivos intermedios')
    parser.add_argument('-c', '--config', default='config.json', help='Archivo de configuración (default: config.json)')
    
    args = parser.parse_args()
    
    video_file = args.video
    
    if not os.path.exists(video_file):
        print(f"Error: El archivo {video_file} no existe")
        sys.exit(1)
    
    # Check if ffmpeg is available
    config_path = args.config
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        print(f"Warning: Config {config_path} no encontrado, usando defaults")
    
    # Override config with command-line args
    if args.output:
        config['output_directory'] = args.output
    if args.temp:
        config['temp_directory'] = args.temp
    
    ffmpeg_cmd = config.get("ffmpeg_path", "ffmpeg")
    
    try:
        subprocess.run([ffmpeg_cmd, '-version'], capture_output=True, check=True)
    except:
        print("Error: ffmpeg no encontrado. Asegúrate de tenerlo en PATH o configurado en config.json")
        sys.exit(1)
    
    # Process video
    processor = HybridVideoProcessor(video_file, config)
    processor.process()


if __name__ == "__main__":
    main()
