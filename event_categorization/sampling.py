import subprocess
import logging
from pathlib import Path
from typing import List
import time

logger = logging.getLogger(__name__)


def _run_cmd(cmd, retries=2, retry_delay=0.5):
    for attempt in range(1, retries + 1):
        try:
            logger.debug("Running command: %s", " ".join(cmd))
            res = subprocess.run(cmd, capture_output=True, check=True)
            logger.debug("Command finished: returncode=%s", res.returncode)
            return res
        except subprocess.CalledProcessError as exc:
            logger.warning("Command failed (attempt %d/%d): %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(retry_delay)
            else:
                raise


def sample_frames(video_path: str, sampling_stride: int, output_dir: str, ffmpeg_path: str) -> List[str]:
    """
    Extract one frame every `sampling_stride` frames (or seconds depending on ffmpeg usage).

    Returns list of output file paths.
    """
    video = Path(video_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg to extract frames at a regular interval. We'll use -vf select to pick every Nth frame
    # but keep the approach simple: use -vsync 0 and -frame_pts to keep deterministic names.

    output_pattern = str(out_dir / "frame_%04d.png")

    cmd = [
        ffmpeg_path,
        '-i', str(video),
        '-vf', f"select=not(mod(n\,{sampling_stride}))",
        '-vsync', '0',
        '-frame_pts', '1',
        output_pattern
    ]

    logger.info("Extracting frames from %s every %d frames into %s", video, sampling_stride, out_dir)
    _run_cmd(cmd)

    # Collect created files (sorted)
    files = sorted([str(p) for p in out_dir.glob('frame_*.png')])
    logger.info("Extracted %d frames", len(files))
    return files
