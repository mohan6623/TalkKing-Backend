"""Groq Whisper v3 transcription service — speech-to-text with filler word detection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
import httpx
from app.config import settings


# Common English filler words to detect
FILLER_WORDS = {"um", "uh", "like", "you know", "basically", "actually", "literally", "right", "so", "well"}

# Weak/hedging phrases
WEAK_PHRASE_PATTERNS = [
    r"\bi think\b", r"\bi guess\b", r"\bmaybe\b", r"\bkind of\b",
    r"\bsort of\b", r"\bprobably\b", r"\bjust\b", r"\ba little\b",
]


@dataclass
class TranscriptResult:
    """Result from Groq Whisper transcription."""
    text: str
    filler_words: list[dict] = field(default_factory=list)  # [{word, count}]
    weak_phrases: list[dict] = field(default_factory=list)  # [{phrase, count}]
    wpm: int = 0
    duration_seconds: float = 300.0  # default 5 minutes


def _count_filler_words(text: str) -> list[dict]:
    """Count occurrences of filler words in transcript."""
    text_lower = text.lower()
    results = []
    for filler in FILLER_WORDS:
        count = text_lower.count(filler)
        if count > 0:
            results.append({"word": filler, "count": count})
    return sorted(results, key=lambda x: x["count"], reverse=True)


def _count_weak_phrases(text: str) -> list[dict]:
    """Count occurrences of weak/hedging phrases in transcript."""
    text_lower = text.lower()
    results = []
    for pattern in WEAK_PHRASE_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            phrase = pattern.replace(r"\b", "").replace("\\b", "")
            results.append({"phrase": phrase, "count": len(matches)})
    return sorted(results, key=lambda x: x["count"], reverse=True)


def _calculate_wpm(text: str, duration_seconds: float = 300.0) -> int:
    """Calculate words per minute from transcript text."""
    if not text.strip():
        return 0
    word_count = len(text.split())
    minutes = max(duration_seconds / 60.0, 0.1)
    return int(word_count / minutes)


async def transcribe_audio(
    audio_bytes: bytes,
    duration_seconds: float = 300.0,
) -> TranscriptResult:
    """Send audio to Groq Whisper v3 for transcription.

    Args:
        audio_bytes: Raw audio data
        duration_seconds: Recording duration for WPM calculation

    Returns:
        TranscriptResult with text, filler words, weak phrases, and WPM
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            files={"file": ("audio.webm", audio_bytes, "audio/webm")},
            data={"model": "whisper-large-v3", "language": "en"},
        )
        response.raise_for_status()
        data = response.json()

    text = data.get("text", "")

    return TranscriptResult(
        text=text,
        filler_words=_count_filler_words(text),
        weak_phrases=_count_weak_phrases(text),
        wpm=_calculate_wpm(text, duration_seconds),
        duration_seconds=duration_seconds,
    )
