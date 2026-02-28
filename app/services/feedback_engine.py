"""Feedback engine — calculates composite scores across 6 dimensions from AI results."""
from __future__ import annotations

from app.services.groq_service import TranscriptResult
from app.services.gemini_service import BoldnessResult
from app.services.hume_service import AcousticsResult


def _calculate_clarity_score(transcript: TranscriptResult) -> dict:
    """Calculate clarity score from transcript analysis.

    Factors: filler word density, WPM (ideal: 120-160), total filler count.
    """
    base_score = 85  # start high, deduct for issues

    # Deduct for filler words
    total_fillers = sum(fw["count"] for fw in transcript.filler_words)
    filler_penalty = min(total_fillers * 3, 40)  # max 40 point penalty
    base_score -= filler_penalty

    # Deduct for WPM outside ideal range
    if transcript.wpm < 100:
        base_score -= 10  # too slow
    elif transcript.wpm > 180:
        base_score -= 10  # too fast

    score = max(0, min(100, base_score))

    # Generate feedback
    if total_fillers == 0:
        feedback = "Excellent clarity — no filler words detected."
    elif total_fillers <= 3:
        feedback = "Good clarity with minimal filler words."
    else:
        top_filler = transcript.filler_words[0]["word"] if transcript.filler_words else "um"
        feedback = f"Work on reducing filler words, especially '{top_filler}'."

    return {
        "score": score,
        "filler_words": transcript.filler_words,
        "wpm": transcript.wpm,
        "feedback": feedback,
    }


def _calculate_vocal_quality(acoustics: AcousticsResult) -> dict:
    """Map acoustics result to vocal quality sub-schema."""
    return {
        "score": acoustics.score,
        "breathing": acoustics.breathing,
        "vocal_fry": acoustics.vocal_fry,
        "raspiness": acoustics.raspiness,
        "feedback": acoustics.feedback,
    }


def _calculate_musicality(acoustics: AcousticsResult) -> dict:
    """Calculate musicality score from pitch variation data."""
    # Base from acoustics, adjusted for pitch quality
    score = acoustics.score
    if acoustics.monotone:
        score = min(score, 45)  # cap if monotone
    elif acoustics.pitch_variation == "dynamic":
        score = min(score + 10, 100)  # bonus for dynamic pitch

    if acoustics.monotone:
        feedback = "Your delivery sounds monotone. Try varying your pitch to keep listeners engaged."
    elif acoustics.pitch_variation == "dynamic":
        feedback = "Great vocal variety — your pitch keeps the audience engaged."
    else:
        feedback = "Decent pitch variation. Push for more dynamic expression."

    return {
        "score": score,
        "pitch_variation": acoustics.pitch_variation,
        "monotone": acoustics.monotone,
        "feedback": feedback,
    }


def _calculate_boldness(boldness: BoldnessResult) -> dict:
    """Map boldness result to sub-schema."""
    return {
        "score": boldness.score,
        "weak_phrases": boldness.weak_phrases,
        "feedback": boldness.feedback,
    }


def _identify_improvements(clarity: dict, vocal: dict, musicality: dict, boldness: dict) -> list[str]:
    """Identify the top areas for improvement."""
    areas = []
    scores = [
        ("Clarity (filler words)", clarity["score"]),
        ("Vocal Quality", vocal["score"]),
        ("Musicality (pitch variation)", musicality["score"]),
        ("Boldness (confident language)", boldness["score"]),
    ]
    # Sort by score ascending — weakest areas first
    scores.sort(key=lambda x: x[1])
    for name, score in scores[:2]:  # top 2 weakest
        if score < 80:
            areas.append(f"Improve {name} (currently {score}/100)")
    return areas


def _identify_strengths(clarity: dict, vocal: dict, musicality: dict, boldness: dict) -> list[str]:
    """Identify the top strengths."""
    strengths = []
    scores = [
        ("Clarity", clarity["score"]),
        ("Vocal Quality", vocal["score"]),
        ("Musicality", musicality["score"]),
        ("Boldness", boldness["score"]),
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    for name, score in scores[:2]:  # top 2 strongest
        if score >= 70:
            strengths.append(f"Strong {name} ({score}/100)")
    return strengths


def _generate_tips(clarity: dict, musicality: dict, boldness: dict) -> list[str]:
    """Generate personalized tips based on scores."""
    tips = []
    if clarity["score"] < 70:
        tips.append("Practice pausing instead of using filler words.")
    if musicality.get("monotone"):
        tips.append("Try reading passages with exaggerated pitch to build range.")
    if boldness["score"] < 70:
        tips.append("Replace 'I think' with 'I believe' or direct statements.")
    if not tips:
        tips.append("Keep practicing consistently to maintain your skills!")
    return tips


def _determine_layer(overall_score: int) -> int:
    """Recommend a confidence layer based on the overall score."""
    if overall_score >= 90:
        return 6
    elif overall_score >= 80:
        return 5
    elif overall_score >= 70:
        return 4
    elif overall_score >= 55:
        return 3
    elif overall_score >= 40:
        return 2
    return 1


def calculate_scores(
    session_id: str,
    transcript: TranscriptResult,
    acoustics: AcousticsResult,
    boldness: BoldnessResult,
    eye_contact: dict | None = None,
    body_language: dict | None = None,
) -> dict:
    """Calculate composite feedback scores from all AI results.

    Args:
        session_id: The recording session ID
        transcript: Groq Whisper result
        acoustics: Hume AI result
        boldness: Gemini result
        eye_contact: Optional MediaPipe eye tracking (from frontend)
        body_language: Optional MediaPipe body tracking (from frontend)

    Returns:
        Complete feedback report dict ready for Supabase storage
    """
    clarity = _calculate_clarity_score(transcript)
    vocal = _calculate_vocal_quality(acoustics)
    music = _calculate_musicality(acoustics)
    bold = _calculate_boldness(boldness)

    # Calculate overall score (weighted average of available dimensions)
    dimension_scores = [clarity["score"], vocal["score"], music["score"], bold["score"]]
    weights = [0.25, 0.25, 0.25, 0.25]

    if eye_contact:
        dimension_scores.append(eye_contact["score"])
        weights = [0.20, 0.20, 0.20, 0.20, 0.10, 0.10]
    if body_language:
        dimension_scores.append(body_language["score"])
        if not eye_contact:
            weights = [0.22, 0.22, 0.22, 0.22, 0.12]

    overall = int(sum(s * w for s, w in zip(dimension_scores, weights)))
    overall = max(0, min(100, overall))

    improvements = _identify_improvements(clarity, vocal, music, bold)
    strengths = _identify_strengths(clarity, vocal, music, bold)
    tips = _generate_tips(clarity, music, bold)

    return {
        "session_id": session_id,
        "overall_score": overall,
        "clarity": clarity,
        "vocal_quality": vocal,
        "musicality": music,
        "boldness": bold,
        "eye_contact": eye_contact,
        "body_language": body_language,
        "improvements": improvements,
        "strengths": strengths,
        "next_level_recommendation": f"Target overall score of {min(overall + 10, 100)} in your next session.",
        "personalized_tips": tips,
        "recommended_layer": _determine_layer(overall),
    }
