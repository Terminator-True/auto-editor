from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from detectors.template_detector import TemplateDetector
from event_categorization.llm_wrapper import VisionLLMWrapper


def analyze_timestamp(video_path: str, timestamp: float, region_norm: Optional[tuple] = None, ffmpeg_path: str = "ffmpeg") -> Dict[str, Any]:
    """Analyze a specific timestamp in a video.

    Steps:
    - Extract frame via TemplateDetector.extract_frame
    - If region_norm provided, crop region when calling detector
    - Use VisionLLMWrapper.analyze_frame to get a textual description
    - Use TemplateDetector.detect_template_in_frame to find known templates

    Returns a dict with fields per spec.
    """
    video = Path(video_path)
    td = TemplateDetector(ffmpeg_path=ffmpeg_path)

    temp_frame = Path(f"temp_analyze_{int(timestamp)}.png")

    result: Dict[str, Any] = {
        'timestamp': timestamp,
        'templates_found': [],
        'llm_description': None,
        'suggested_event': None,
        'confidence': 'low'
    }

    # Extract frame
    if not td.extract_frame(video, timestamp, temp_frame):
        logger.warning("analyze_timestamp: failed to extract frame at %s", timestamp)
        return result

    # Run template matching across loaded templates
    for template_name in td.templates.keys():
        try:
            found = td.detect_template_in_frame(str(temp_frame), template_name, threshold=td.templates.get('threshold', 80), region=region_norm, normalized=True, video_resolution=td.video_resolution)
        except Exception:
            found = False

        if found:
            result['templates_found'].append(template_name)

    # LLM analysis (best-effort)
    llm = VisionLLMWrapper(ffmpeg_path=ffmpeg_path)
    # Try to classify first (lighter) then full analysis
    classification = llm.classify_frame(str(temp_frame))
    if classification:
        result['llm_description'] = classification.get('description')
        result['suggested_event'] = classification.get('event_type')
        result['confidence'] = classification.get('confidence', 'low')
    else:
        # fallback to analyze_frame for textual description
        desc = llm.analyze_frame(str(temp_frame))
        if desc:
            result['llm_description'] = desc
            # naive suggestion: take first word as event
            result['suggested_event'] = desc.split()[0].lower() if desc else None
            result['confidence'] = 'medium'

    # Cleanup
    try:
        if temp_frame.exists():
            temp_frame.unlink()
    except Exception:
        pass

    # If templates were found, boost confidence
    if result['templates_found']:
        result['confidence'] = 'high'

    return result
