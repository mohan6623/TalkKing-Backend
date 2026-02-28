"""Assessment routes — POST /demo/assess (public, no auth required)."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from app.core.exceptions import AudioTooLargeError
from app.services.audio_utils import validate_audio_size
from app.schemas.assessment import DemoAssessmentResult
from app.core.redis_client import get_redis_pool

router = APIRouter(prefix="/demo", tags=["demo"])

# Rate limit: max 5 demo assessments per IP per hour
_RATE_LIMIT = 5
_RATE_WINDOW = 3600  # seconds


def _to_10(score_100: int) -> int:
    """Convert a 0-100 score to a 1-10 scale."""
    return max(1, min(10, round(score_100 / 10)))


def _overall_level(score_10: int) -> str:
    if score_10 >= 9:
        return "expert"
    if score_10 >= 8:
        return "advanced"
    if score_10 >= 7:
        return "upper-intermediate"
    if score_10 >= 5:
        return "intermediate"
    if score_10 >= 3:
        return "elementary"
    return "beginner"


@router.post("/assess", response_model=DemoAssessmentResult)
async def demo_assess(
    request: Request,
    audio: UploadFile = File(...),
):
    """Run an anonymous demo assessment on uploaded audio.

    No authentication required. Rate-limited to prevent abuse.
    Returns a full DemoAssessmentResult.
    Runs directly (not via Celery) since demo sessions are small.
    """
    # Rate limiting by IP (supports reverse proxy via X-Forwarded-For)
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    rate_key = f"demo_rate:{client_ip}"
    try:
        redis = get_redis_pool()
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, _RATE_WINDOW)
        if count > _RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Too many demo requests. Please try again later.")
    except HTTPException:
        raise
    except Exception:
        pass  # If Redis is down, allow the request through

    audio_bytes = await audio.read()

    if not validate_audio_size(audio_bytes, max_mb=10):  # stricter limit for demo
        raise AudioTooLargeError(max_mb=10)

    # Run analysis directly (synchronous for demo — short audio only)
    from app.services.ai_orchestrator import analyze_recording
    session_id = str(uuid.uuid4())
    feedback = await analyze_recording(audio_bytes, "tech-interview", session_id)

    # Convert 0-100 scores to 1-10 scale for demo UI
    clarity_10 = _to_10(feedback["clarity"]["score"])
    vocal_10 = _to_10(feedback["vocal_quality"]["score"])
    musicality_10 = _to_10(feedback["musicality"]["score"])
    boldness_10 = _to_10(feedback["boldness"]["score"])
    overall_10 = _to_10(feedback["overall_score"])

    # Determine top dimension
    dim_scores = [
        ("Clarity", clarity_10),
        ("Vocal Quality", vocal_10),
        ("Musicality", musicality_10),
        ("Boldness", boldness_10),
    ]
    top_dim = max(dim_scores, key=lambda x: x[1])

    # Build suggestions from tips + dimension data
    suggestions = []
    for dim_name, dim_score in dim_scores:
        if dim_score < 8:
            suggestions.append({
                "dimension": dim_name,
                "score": dim_score,
                "tip": next(
                    (t for t in feedback.get("personalized_tips", []) if dim_name.lower().split()[0] in t.lower()),
                    f"Practice to improve your {dim_name}.",
                ),
                "layer_link": feedback.get("recommended_layer", 1),
            })

    return DemoAssessmentResult(
        id=session_id,
        duration=0,
        recorded_at=datetime.now(timezone.utc).isoformat(),
        scores={
            "clarity": clarity_10,
            "vocal": vocal_10,
            "musicality": musicality_10,
            "boldness": boldness_10,
        },
        overall_score=overall_10,
        overall_level=_overall_level(overall_10),
        feedback=feedback.get("next_level_recommendation", "Keep practicing to level up!"),
        suggestions=suggestions,
        filler_words=feedback["clarity"].get("filler_words", []),
        weak_phrases=feedback["boldness"].get("weak_phrases", []),
        wpm=feedback["clarity"].get("wpm", 0),
        recommended_layer=feedback.get("recommended_layer", 1),
        teaser_data={
            "overall_score": overall_10,
            "highlights": feedback.get("strengths", [])[:2] or ["Analyze more to see your strengths!"],
            "top_dimension": top_dim[0],
        },
    )
