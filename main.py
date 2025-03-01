import cv2
import numpy as np
import librosa
import ffmpeg
import pytesseract
from moviepy import VideoFileClip
from PIL import Image
import os
import multiprocessing
import sys
import json

# Lista compartida para evitar clips demasiado cercanos
processed_timestamps = []

def is_valid_timestamp(timestamp, min_gap=30):
    """ Verifica si el timestamp está al menos `min_gap` segundos lejos de los ya procesados. """
    global processed_timestamps
    if not processed_timestamps or all(abs(timestamp - t) >= min_gap for t in processed_timestamps):
        processed_timestamps.append(timestamp)
        return True
    return False

def extract_audio(video_path, audio_path):
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)
    print("[INFO] Audio extraído correctamente.")

def detect_loud_moments(video_path, audio_path, output_folder="highlights", threshold=0.1):
    print("[INFO] Detectando momentos ruidosos...")
    y, sr = librosa.load(audio_path)
    energy = librosa.feature.rms(y=y)[0]
    times = librosa.times_like(energy, sr=sr)
    
    for i in range(len(energy)):
        if energy[i] > threshold:
            timestamp = times[i]
            print(f"[INFO] Momento ruidoso en {timestamp}s")
            if is_valid_timestamp(timestamp):
                cut_highlight_clip(video_path, timestamp, output_folder)    

def detect_visual_changes(video_path, output_folder="highlights", threshold=5000000):
    print("[INFO] Detectando cambios visuales...")
    cap = cv2.VideoCapture(video_path)
    prev_frame = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            score = np.sum(diff)
            if score > threshold:
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if is_valid_timestamp(timestamp):
                    cut_highlight_clip(video_path, timestamp, output_folder)
        prev_frame = gray
    cap.release()

def detect_text_in_frames(video_path, output_folder="highlights"):
    try:
        with open("config.json") as file:
            config = json.load(file)
                        
        print("[INFO] Detectando texto en los frames...")
        cap = cv2.VideoCapture(video_path)
        frame_skip = 30
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_skip == 0:
                text = pytesseract.image_to_string(Image.fromarray(frame))
                if any(keyword in text.lower() for keyword in config['keyWords']):
                    timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                    if is_valid_timestamp(timestamp):
                        print(f"[INFO] Texto encontrado en {timestamp}s")
                        cut_highlight_clip(video_path, timestamp, output_folder)
            frame_count += 1
        cap.release()
    except Exception as e:
        print(f"[ERROR] {e}")

def cut_highlight_clip(video_path, timestamp, output_folder="highlights", clip_duration=60):
    print(f"[INFO] Cortando clip en {timestamp}s...")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    start_time = max(0, timestamp - clip_duration // 2)
    end_time = start_time + clip_duration
    output_file = os.path.join(output_folder, f"highlight_{int(timestamp)}.mp4")

    print(f"[INFO] Guardando clip en {output_file}")

    ffmpeg.input(video_path, ss=start_time, to=end_time).output(output_file).run(
        cmd='.\\ffmpeg\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe')

    print("[INFO] Clip guardado correctamente.")

def main(video_path):
    cv2.ocl.setUseOpenCL(True)
    print("[INFO] OpenCL habilitado:", cv2.ocl.useOpenCL())

    audio_path = "temp_audio.wav"
    extract_audio(video_path, audio_path)

    # Evita problemas con multiprocessing y variables compartidas
    manager = multiprocessing.Manager()
    global processed_timestamps
    processed_timestamps = manager.list()

    with multiprocessing.Pool(processes=3) as pool:
        pool.apply_async(detect_loud_moments, (video_path, audio_path))
        pool.apply_async(detect_text_in_frames, (video_path,))
        pool.close()
        pool.join()

    print("[INFO] Proceso finalizado")

if __name__ == "__main__":
    sys.argv = ["main.py", ".\\gameplay.mp4"]
    if len(sys.argv) != 2:
        print("Usage: python main.py <video_file>")
        sys.exit(1)
    if not os.path.exists('ffmpeg'):
        print("Error: ffmpeg folder not found, download ffmpeg from https://ffmpeg.org/download.html and extract it to the root folder")
        sys.exit(1)
    
    video_file = sys.argv[1]
    main(video_file)
