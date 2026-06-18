"""
Silence Detection and Removal using ffmpeg
"""

import subprocess
import re
from pathlib import Path


class SilenceDetector:
    def __init__(self, ffmpeg_path="ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
    
    def detect_silence_periods(self, video_path, noise_threshold=-40, min_duration=1.0):
        """
        Detect silence periods in video using ffmpeg silencedetect filter
        
        Args:
            video_path: Path to video file
            noise_threshold: Noise level in dB (more negative = more strict)
            min_duration: Minimum silence duration in seconds
            
        Returns:
            List of tuples [(start, end), ...] with silence periods
        """
        cmd = [
            self.ffmpeg_path,
            '-i', str(video_path),
            '-af', f'silencedetect=noise={noise_threshold}dB:d={min_duration}',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            silence_periods = []
            silence_start = None
            
            for line in result.stderr.split('\n'):
                if 'silencedetect' in line:
                    if 'silence_start' in line:
                        match = re.search(r'silence_start: ([\d.]+)', line)
                        if match:
                            silence_start = float(match.group(1))
                    
                    elif 'silence_end' in line and silence_start is not None:
                        match = re.search(r'silence_end: ([\d.]+)', line)
                        if match:
                            silence_end = float(match.group(1))
                            silence_periods.append((silence_start, silence_end))
                            silence_start = None
            
            print(f"[SilenceDetector] Detectados {len(silence_periods)} períodos de silencio")
            return silence_periods
            
        except Exception as e:
            print(f"[SilenceDetector ERROR] {e}")
            return []
    
    def remove_silence(self, video_path, output_path, noise_threshold=-40, min_duration=1.0):
        """
        Remove silence from video using ffmpeg silenceremove filter
        
        Args:
            video_path: Input video path
            output_path: Output video path
            noise_threshold: Noise level in dB
            min_duration: Minimum silence duration to remove
            
        Returns:
            True if successful, False otherwise
        """
        cmd = [
            self.ffmpeg_path,
            '-i', str(video_path),
            '-af', f'silenceremove=start_periods=1:start_threshold={noise_threshold}dB:start_duration={min_duration}:'
                   f'stop_periods=-1:stop_threshold={noise_threshold}dB:stop_duration={min_duration}',
            '-c:v', 'copy',  # Copy video stream (no re-encoding)
            '-y',
            str(output_path)
        ]
        
        try:
            print(f"[SilenceDetector] Eliminando silencios...")
            result = subprocess.run(cmd, check=True, capture_output=True)
            print(f"[SilenceDetector] ✓ Video sin silencios: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[SilenceDetector ERROR] Error eliminando silencios: {e}")
            return False
    
    def get_active_periods(self, video_path, duration, noise_threshold=-40, min_silence=1.0):
        """
        Get periods with activity (inverse of silence periods)
        
        Args:
            video_path: Path to video
            duration: Total video duration in seconds
            noise_threshold: Noise threshold in dB
            min_silence: Minimum silence duration
            
        Returns:
            List of tuples [(start, end), ...] with active periods
        """
        silence_periods = self.detect_silence_periods(video_path, noise_threshold, min_silence)
        
        if not silence_periods:
            return [(0, duration)]
        
        active_periods = []
        current_time = 0
        
        for silence_start, silence_end in silence_periods:
            if current_time < silence_start:
                active_periods.append((current_time, silence_start))
            current_time = silence_end
        
        # Add final period if exists
        if current_time < duration:
            active_periods.append((current_time, duration))
        
        return active_periods
