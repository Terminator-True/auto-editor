"""
Template Matching Detector for game-specific UI elements
Lightweight detection using PIL instead of OpenCV
"""

from PIL import Image, ImageChops, ImageStat
from pathlib import Path
import subprocess
import json


class TemplateDetector:
    def __init__(self, ffmpeg_path="ffmpeg", templates_dir="templates", temp_dir=None):
        self.ffmpeg_path = ffmpeg_path
        self.templates_dir = Path(templates_dir)
        self.templates = {}
        self.video_resolution = None  # Cache video resolution
        self.temp_dir = Path(temp_dir) if temp_dir else Path.cwd()
        
        # Load templates if directory exists
        if self.templates_dir.exists():
            self._load_templates()
    
    def _load_templates(self):
        """Load template images from templates directory"""
        for template_file in self.templates_dir.glob("*.png"):
            template_name = template_file.stem
            try:
                self.templates[template_name] = Image.open(template_file)
                print(f"[TemplateDetector] Cargado template: {template_name}")
            except Exception as e:
                print(f"[TemplateDetector WARNING] No se pudo cargar {template_file}: {e}")
    
    def add_template(self, name, image_path):
        """Add a new template image"""
        try:
            self.templates[name] = Image.open(image_path)
            print(f"[TemplateDetector] Template '{name}' agregado")
        except Exception as e:
            print(f"[TemplateDetector ERROR] Error cargando template {name}: {e}")
    
    def get_video_resolution(self, video_path):
        """
        Get video resolution using ffprobe
        
        Returns:
            tuple: (width, height) or None if error
        """
        if self.video_resolution:
            return self.video_resolution
        
        # Try multiple ffprobe paths (absolute, relative, system PATH)
        ffprobe_candidates = [
            self.ffmpeg_path.replace('ffmpeg', 'ffprobe'),
            self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe'),
            Path(self.ffmpeg_path).parent / 'ffprobe.exe',
            Path(self.ffmpeg_path).parent / 'ffprobe',
            'ffprobe',
            'ffprobe.exe'
        ]
        
        for ffprobe_path in ffprobe_candidates:
            cmd = [
                str(ffprobe_path),
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'json',
                str(video_path)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
                data = json.loads(result.stdout)
                width = data['streams'][0]['width']
                height = data['streams'][0]['height']
                self.video_resolution = (width, height)
                print(f"[TemplateDetector] Resolución detectada: {width}x{height}")
                return (width, height)
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                print(f"[TemplateDetector WARNING] ffprobe timeout en {ffprobe_path}")
                continue
            except Exception as e:
                continue
        
        # All attempts failed
        print("[TemplateDetector ERROR] No se pudo obtener resolución del video")
        print("[TemplateDetector ERROR] Razones posibles:")
        print("  1. ffprobe no está en PATH")
        print("  2. Ruta de ffmpeg incorrecta en config.json")
        print("  3. El video está corrupto")
        print("[TemplateDetector ERROR] Soluciones:")
        print("  - Instala ffmpeg: winget install Gyan.FFmpeg")
        print("  - O verifica ruta en config.json: ffmpeg_path")
        return None
    
    def normalize_region(self, region, from_resolution):
        """
        Convert pixel coordinates to normalized (0-1) coordinates
        
        Args:
            region: (x, y, width, height) in pixels
            from_resolution: (width, height) of reference resolution
            
        Returns:
            (x_norm, y_norm, w_norm, h_norm) as fractions (0-1)
        """
        x, y, w, h = region
        ref_width, ref_height = from_resolution
        
        return (
            x / ref_width,
            y / ref_height,
            w / ref_width,
            h / ref_height
        )
    
    def denormalize_region(self, region_norm, to_resolution):
        """
        Convert normalized (0-1) coordinates to pixel coordinates
        
        Args:
            region_norm: (x_norm, y_norm, w_norm, h_norm) as fractions (0-1)
            to_resolution: (width, height) target resolution
            
        Returns:
            (x, y, width, height) in pixels
        """
        x_norm, y_norm, w_norm, h_norm = region_norm
        target_width, target_height = to_resolution
        
        return (
            int(x_norm * target_width),
            int(y_norm * target_height),
            int(w_norm * target_width),
            int(h_norm * target_height)
        )
    
    def extract_frame(self, video_path, timestamp, output_path):
        """Extract a single frame from video at given timestamp"""
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
    
    def compare_images(self, img1, img2, region=None, normalized=False, video_resolution=None):
        """
        Compare two images and return similarity score
        
        Args:
            img1: First PIL Image
            img2: Second PIL Image
            region: Region to compare - (x, y, width, height)
            normalized: If True, region is in 0-1 coordinates, otherwise pixels
            video_resolution: Required if normalized=True, tuple (width, height)
            
        Returns:
            Similarity score (0-100, higher = more similar)
        """
        # Resize images to match if needed
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
        
        # Crop to region if specified
        if region:
            # Convert normalized to pixels if needed
            if normalized:
                if not video_resolution:
                    video_resolution = img2.size  # Use image size as fallback
                region = self.denormalize_region(region, video_resolution)
            
            x, y, w, h = region
            img1 = img1.crop((x, y, x + w, y + h))
            img2 = img2.crop((x, y, x + w, y + h))
        
        # Calculate difference
        diff = ImageChops.difference(img1.convert('RGB'), img2.convert('RGB'))
        stat = ImageStat.Stat(diff)
        
        # Average difference across all channels (0-255)
        avg_diff = sum(stat.mean) / len(stat.mean)
        
        # Convert to similarity percentage
        similarity = max(0, 100 - (avg_diff / 255 * 100))
        
        return similarity
    
    def detect_template_in_frame(self, frame_path, template_name, threshold=80, region=None, normalized=False, video_resolution=None):
        """
        Detect if a template appears in a frame
        
        Args:
            frame_path: Path to frame image
            template_name: Name of template to search for
            threshold: Similarity threshold (0-100)
            region: Region to search in - (x, y, width, height)
            normalized: If True, region is in 0-1 coordinates
            video_resolution: Required if normalized=True
            
        Returns:
            True if template found, False otherwise
        """
        if template_name not in self.templates:
            print(f"[TemplateDetector WARNING] Template '{template_name}' no encontrado")
            return False
        
        try:
            frame = Image.open(frame_path)
            template = self.templates[template_name]
            
            # Use frame resolution if not provided
            if normalized and not video_resolution:
                video_resolution = frame.size
            
            similarity = self.compare_images(template, frame, region, normalized, video_resolution)
            
            return similarity >= threshold
            
        except Exception as e:
            print(f"[TemplateDetector ERROR] Error comparando: {e}")
            return False
    
    def scan_video(self, video_path, template_name, interval=10, threshold=80, region=None, normalized=False):
        """
        Scan video for template matches at regular intervals
        
        Args:
            video_path: Path to video file
            template_name: Template to search for
            interval: Seconds between frame checks
            threshold: Similarity threshold
            region: Region to check - (x, y, width, height)
            normalized: If True, region is in 0-1 coordinates
            
        Returns:
            List of timestamps where template was found
        """
        if template_name not in self.templates:
            print(f"[TemplateDetector ERROR] Template '{template_name}' no encontrado")
            return []
        
        # Get video resolution first
        video_resolution = self.get_video_resolution(video_path)
        if not video_resolution:
            return []
        
        print(f"[TemplateDetector] Resolución del video: {video_resolution[0]}x{video_resolution[1]}")
        
        # Get video duration
        duration = self._get_video_duration(video_path)
        if duration is None:
            return []
        
        matches = []
        temp_frame = self.temp_dir / f"temp_frame_{template_name}.png"
        
        print(f"[TemplateDetector] Escaneando video en busca de '{template_name}'...")
        
        timestamp = 0
        while timestamp < duration:
            if self.extract_frame(video_path, timestamp, temp_frame):
                if self.detect_template_in_frame(temp_frame, template_name, threshold, region, normalized, video_resolution):
                    matches.append(timestamp)
                    print(f"  ✓ Match encontrado en {timestamp}s")
            
            timestamp += interval
        
        # Cleanup
        if temp_frame.exists():
            temp_frame.unlink()
        
        print(f"[TemplateDetector] {len(matches)} matches encontrados para '{template_name}'")
        return matches
    
    def _get_video_duration(self, video_path):
        """Get video duration using ffprobe"""
        cmd = [
            self.ffmpeg_path.replace('ffmpeg', 'ffprobe'),
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            print(f"[TemplateDetector ERROR] No se pudo obtener duración: {e}")
            return None
    
    def create_template_from_video(self, video_path, timestamp, template_name, region=None, normalized=False):
        """
        Extract a frame from video and save it as a template
        
        Args:
            video_path: Source video
            timestamp: Time to extract frame
            template_name: Name for the template
            region: Region to crop - (x, y, width, height)
            normalized: If True, region is in 0-1 coordinates
        """
        self.templates_dir.mkdir(exist_ok=True)
        output_path = self.templates_dir / f"{template_name}.png"
        
        if self.extract_frame(video_path, timestamp, output_path):
            if region:
                img = Image.open(output_path)
                
                # Convert normalized to pixels if needed
                if normalized:
                    video_resolution = img.size
                    region = self.denormalize_region(region, video_resolution)
                    print(f"[TemplateDetector] Región normalizada convertida a: {region}")
                
                # Crop to region
                x, y, w, h = region
                cropped = img.crop((x, y, x + w, y + h))
                cropped.save(output_path)
            
            # Load into memory
            self.templates[template_name] = Image.open(output_path)
            print(f"[TemplateDetector] ✓ Template '{template_name}' creado: {output_path}")
            return True
        
        return False
