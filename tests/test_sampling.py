import os
from pathlib import Path
import subprocess
import tempfile
import shutil

from event_categorization.sampling import sample_frames


def make_test_video(video_path: Path, ffmpeg_path: str):
    # Create a very short test video (10 frames) using ffmpeg with color source
    cmd = [
        ffmpeg_path,
        '-y',
        '-f', 'lavfi',
        '-i', 'color=c=blue:s=160x120:d=1',
        '-vf', 'fps=10',
        str(video_path)
    ]
    subprocess.run(cmd, check=True)


def test_sample_frames(tmp_path):
    ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg', 'bin', 'ffmpeg.exe')
    video = tmp_path / 'test_video.mp4'
    out_dir = tmp_path / 'out'

    make_test_video(video, ffmpeg_path)

    files = sample_frames(str(video), sampling_stride=2, output_dir=str(out_dir), ffmpeg_path=ffmpeg_path)

    # With 10 frames and stride=2 we expect ~5 frames
    assert len(files) >= 4 and len(files) <= 6
    for f in files:
        assert Path(f).exists()
