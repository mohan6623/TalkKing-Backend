"""Hume AI acoustic/emotion analysis service — analyzes vocal quality from audio."""
from __future__ import annotations

from dataclasses import dataclass
import httpx
from app.config import settings


@dataclass
class AcousticsResult:
    """Result from Hume AI prosody analysis."""
    score: int = 0          # 0-100 composite vocal quality score
    breathing: str = "normal"  # shallow | normal | deep
    vocal_fry: bool = False
    raspiness: bool = False
    pitch_variation: str = "moderate"  # flat | moderate | dynamic
    monotone: bool = False
    feedback: str = ""


def _extract_emotion_scores(predictions: list[dict]) -> dict[str, float]:
    """Extract emotion name→score map from Hume predictions."""
    emotions = {}
    for pred_group in predictions:
        for pred in pred_group.get("predictions", []):
            for emotion in pred.get("emotions", []):
                name = emotion.get("name", "")
                score = emotion.get("score", 0.0)
                emotions[name] = score
    return emotions


def _calculate_vocal_score(emotions: dict[str, float]) -> int:
    """Calculate a composite vocal quality score from emotion signals."""
    if not emotions:
        return 50  # neutral default

    # Positive signals boost score
    confidence = emotions.get("Confidence", 0.0)
    excitement = emotions.get("Excitement", 0.0)
    calmness = emotions.get("Calmness", 0.0)
    determination = emotions.get("Determination", 0.0)

    # Negative signals reduce score
    anxiety = emotions.get("Anxiety", 0.0)
    boredom = emotions.get("Boredom", 0.0)
    doubt = emotions.get("Doubt", 0.0)

    positive = (confidence * 30) + (excitement * 20) + (calmness * 15) + (determination * 15)
    negative = (anxiety * 20) + (boredom * 15) + (doubt * 15)

    raw_score = 50 + positive - negative
    return max(0, min(100, int(raw_score)))


def _determine_breathing(emotions: dict[str, float]) -> str:
    """Infer breathing quality from emotional signals."""
    anxiety = emotions.get("Anxiety", 0.0)
    calmness = emotions.get("Calmness", 0.0)
    if anxiety > 0.5:
        return "shallow"
    elif calmness > 0.6:
        return "deep"
    return "normal"


def _determine_pitch_variation(emotions: dict[str, float]) -> tuple[str, bool]:
    """Infer pitch variation and monotone status from emotional signals."""
    excitement = emotions.get("Excitement", 0.0)
    boredom = emotions.get("Boredom", 0.0)

    if boredom > 0.4:
        return "flat", True
    elif excitement > 0.5:
        return "dynamic", False
    return "moderate", False


async def analyze_acoustics(audio_bytes: bytes) -> AcousticsResult:
    """Send audio to Hume AI for prosody/emotion analysis.

    Args:
        audio_bytes: Raw audio data

    Returns:
        AcousticsResult with vocal quality scores and feedback
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.hume.ai/v0/batch/jobs",
            headers={
                "X-Hume-Api-Key": settings.HUME_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "models": {"prosody": {}},
                "urls": [],  # Will use file upload in production
            },
            files={"file": ("audio.webm", audio_bytes, "audio/webm")},
        )
        response.raise_for_status()
        data = response.json()

    # Extract predictions from Hume response structure
    predictions = []
    try:
        results = data.get("results", {}).get("predictions", [])
        for result in results:
            models = result.get("models", {})
            prosody = models.get("prosody", {})
            grouped = prosody.get("grouped_predictions", [])
            predictions.extend(grouped)
    except (KeyError, TypeError):
        pass

    emotions = _extract_emotion_scores(predictions)
    score = _calculate_vocal_score(emotions)
    breathing = _determine_breathing(emotions)
    pitch_var, monotone = _determine_pitch_variation(emotions)

    # Generate feedback
    feedback_parts = []
    if score >= 80:
        feedback_parts.append("Excellent vocal presence.")
    elif score >= 60:
        feedback_parts.append("Good vocal quality with room for improvement.")
    else:
        feedback_parts.append("Focus on vocal confidence and energy.")

    if monotone:
        feedback_parts.append("Try varying your pitch to keep listeners engaged.")
    if breathing == "shallow":
        feedback_parts.append("Practice deep breathing to support your voice.")

    return AcousticsResult(
        score=score,
        breathing=breathing,
        vocal_fry=False,  # Hume doesn't directly detect this
        raspiness=False,
        pitch_variation=pitch_var,
        monotone=monotone,
        feedback=" ".join(feedback_parts),
    )
