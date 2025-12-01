from pathlib import Path
from typing import List, Union
from pydub.utils import mediainfo

def get_total_audio_duration_ms(audio_files: Union[Path, str, List[Union[Path, str]]]) -> int:
    """
    Calculate total duration (in milliseconds) of one or multiple audio files.

    Args:
        audio_files: a single audio file path or a list of audio file paths.

    Returns:
        Total duration in milliseconds (int).
    """
    if not audio_files:
        return 0

    if isinstance(audio_files, (str, Path)):
        audio_files = [audio_files]

    total_ms = 0
    for path in audio_files:
        try:
            info = mediainfo(str(path))
            dur_sec = float(info.get("duration", 0.0))
            total_ms += int(dur_sec * 1000)
        except Exception:
            continue

    return total_ms
