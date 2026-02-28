"""Audio utility functions — validation, format detection, duration estimation."""
from __future__ import annotations


MAX_AUDIO_SIZE_MB = 25
ESTIMATED_BITRATE_BPS = 128_000  # 128 kbps — conservative estimate


def validate_audio_size(audio_bytes: bytes, max_mb: int = MAX_AUDIO_SIZE_MB) -> bool:
    """Return True if audio is within the allowed size limit."""
    max_bytes = max_mb * 1024 * 1024
    return len(audio_bytes) <= max_bytes


def get_audio_duration_estimate(audio_bytes: bytes) -> float:
    """Estimate audio duration in seconds from byte size.

    Uses a conservative 128kbps bitrate assumption.
    For accurate duration, pydub would be used in production.
    """
    if len(audio_bytes) == 0:
        return 0.0
    bytes_per_second = ESTIMATED_BITRATE_BPS / 8
    return len(audio_bytes) / bytes_per_second
