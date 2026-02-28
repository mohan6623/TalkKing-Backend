"""AI Orchestrator — parallel fan-out to AI providers and score calculation.

Flow:
  Phase 1 (parallel): Groq transcription + Hume acoustics (both need raw audio)
  Phase 2 (sequential): Gemini boldness analysis (needs transcript text)
  Phase 3: Calculate composite scores via feedback engine
"""
from __future__ import annotations

import asyncio
from app.services.groq_service import transcribe_audio
from app.services.gemini_service import analyze_boldness
from app.services.hume_service import analyze_acoustics
from app.services.feedback_engine import calculate_scores


async def analyze_recording(
    audio_bytes: bytes,
    user_mission: str,
    session_id: str,
) -> dict:
    """Fan-out to AI providers in parallel, then combine results.

    Memory-conscious: processes audio bytes then frees them.

    Args:
        audio_bytes: Raw audio recording data
        user_mission: User's mission type for context-aware analysis
        session_id: The recording session ID

    Returns:
        Complete feedback report dict
    """
    # Phase 1: Parallel — Groq + Hume both need raw audio
    transcript_result, acoustic_result = await asyncio.gather(
        transcribe_audio(audio_bytes),
        analyze_acoustics(audio_bytes),
    )

    # Free audio bytes from memory ASAP
    del audio_bytes

    # Phase 2: Sequential — Gemini needs the transcript text
    boldness_result = await analyze_boldness(
        transcript=transcript_result.text,
        mission=user_mission,
    )

    # Phase 3: Calculate composite scores across all dimensions
    feedback = calculate_scores(
        session_id=session_id,
        transcript=transcript_result,
        acoustics=acoustic_result,
        boldness=boldness_result,
    )

    return feedback
