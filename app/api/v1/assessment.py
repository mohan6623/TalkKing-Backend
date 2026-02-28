"""Assessment routes — POST /demo/assess (public, no auth required)."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.core.exceptions import AudioTooLargeError
from app.services.audio_utils import validate_audio_size

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/assess")
async def demo_assess(
    audio: UploadFile = File(...),
):
    """Run an anonymous demo assessment on uploaded audio.

    No authentication required. Returns a teaser result for landing page.
    Runs directly (not via Celery) since demo sessions are small.
    """
    audio_bytes = await audio.read()

    if not validate_audio_size(audio_bytes, max_mb=10):  # stricter limit for demo
        raise AudioTooLargeError(max_mb=10)

    # Run analysis directly (synchronous for demo — short audio only)
    from app.services.ai_orchestrator import analyze_recording
    feedback = await analyze_recording(audio_bytes, "tech-interview", "demo")

    # Build teaser data (limited info for unregistered users)
    return {
        "overall_score": feedback["overall_score"],
        "highlights": feedback.get("strengths", [])[:2],
        "top_dimension": max(
            [
                ("Clarity", feedback["clarity"]["score"]),
                ("Vocal Quality", feedback["vocal_quality"]["score"]),
                ("Musicality", feedback["musicality"]["score"]),
                ("Boldness", feedback["boldness"]["score"]),
            ],
            key=lambda x: x[1],
        )[0],
        "teaser_message": "Sign up to see your full detailed report!",
    }
