"""Tests for AI service modules — Groq, Gemini, Hume (all HTTP mocked with respx)."""
import pytest
import respx
import httpx
from app.services.groq_service import transcribe_audio, TranscriptResult
from app.services.gemini_service import analyze_boldness, BoldnessResult
from app.services.hume_service import analyze_acoustics, AcousticsResult
from app.services.audio_utils import validate_audio_size, get_audio_duration_estimate


# ── Groq Whisper Transcription ───────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_groq_transcription_success():
    """Groq Whisper should return transcript text, filler words, and WPM."""
    respx.post("https://api.groq.com/openai/v1/audio/transcriptions").mock(
        return_value=httpx.Response(200, json={
            "text": "Hello world um I think this is like a great idea",
        })
    )
    result = await transcribe_audio(b"fake-audio-bytes")
    assert isinstance(result, TranscriptResult)
    assert "Hello world" in result.text
    assert result.wpm > 0


@pytest.mark.asyncio
@respx.mock
async def test_groq_transcription_empty():
    """Groq should handle empty transcript gracefully."""
    respx.post("https://api.groq.com/openai/v1/audio/transcriptions").mock(
        return_value=httpx.Response(200, json={"text": ""})
    )
    result = await transcribe_audio(b"silence")
    assert result.text == ""
    assert result.wpm == 0


# ── Gemini Boldness Analysis ─────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_gemini_boldness_success():
    """Gemini should return boldness score, weak phrases, and feedback."""
    respx.post(
        url__startswith="https://generativelanguage.googleapis.com/"
    ).mock(
        return_value=httpx.Response(200, json={
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '{"score": 80, "weak_phrases": [{"phrase": "I think", "count": 2}], "feedback": "Strong language overall"}'
                    }]
                }
            }]
        })
    )
    result = await analyze_boldness("Hello world I think this is great", "tech-interview")
    assert isinstance(result, BoldnessResult)
    assert result.score == 80
    assert len(result.weak_phrases) == 1


@pytest.mark.asyncio
@respx.mock
async def test_gemini_boldness_no_weak_phrases():
    """Gemini should handle transcript with no weak phrases."""
    respx.post(
        url__startswith="https://generativelanguage.googleapis.com/"
    ).mock(
        return_value=httpx.Response(200, json={
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '{"score": 95, "weak_phrases": [], "feedback": "Excellent bold language"}'
                    }]
                }
            }]
        })
    )
    result = await analyze_boldness("This is definitively correct", "sales-pitch")
    assert result.score == 95
    assert result.weak_phrases == []


# ── Hume AI Acoustics ────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_hume_acoustics_success():
    """Hume should return vocal quality scores."""
    respx.post(
        url__startswith="https://api.hume.ai/"
    ).mock(
        return_value=httpx.Response(200, json={
            "results": {
                "predictions": [{
                    "models": {
                        "prosody": {
                            "grouped_predictions": [{
                                "predictions": [{
                                    "emotions": [
                                        {"name": "Confidence", "score": 0.82},
                                        {"name": "Anxiety", "score": 0.15},
                                        {"name": "Excitement", "score": 0.65},
                                    ]
                                }]
                            }]
                        }
                    }
                }]
            }
        })
    )
    result = await analyze_acoustics(b"fake-audio-bytes")
    assert isinstance(result, AcousticsResult)
    assert result.score >= 0
    assert result.breathing in ("shallow", "normal", "deep")


# ── Audio Utils ──────────────────────────────────────────────────────

def test_validate_audio_size_ok():
    """Audio under 25MB should pass validation."""
    data = b"x" * (10 * 1024 * 1024)  # 10MB
    assert validate_audio_size(data) is True


def test_validate_audio_size_too_large():
    """Audio over 25MB should fail validation."""
    data = b"x" * (26 * 1024 * 1024)  # 26MB
    assert validate_audio_size(data) is False


def test_audio_duration_estimate():
    """Duration estimate should return a reasonable value."""
    # 1MB of audio at ~128kbps ≈ ~62 seconds
    data = b"x" * (1 * 1024 * 1024)
    duration = get_audio_duration_estimate(data)
    assert duration > 0
