"""Progress routes — GET /progress (protected)."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("")
async def get_progress(
    current_user: dict = Depends(get_current_user),
):
    """Get historical progress chart data from Supabase feedback reports."""
    user_id = current_user.get("sub")
    supabase = get_supabase()

    # Get all feedback reports for this user's sessions, ordered by date
    result = supabase.table("feedback_reports").select(
        "session_id, overall_score, clarity, vocal_quality, musicality, boldness, eye_contact, body_language, created_at"
    ).eq("user_id", user_id).order("created_at").execute()

    # Transform into ProgressData format
    progress = []
    for row in (result.data or []):
        progress.append({
            "date": row.get("created_at", ""),
            "overall_score": row.get("overall_score", 0),
            "clarity": row.get("clarity", {}).get("score", 0) if isinstance(row.get("clarity"), dict) else 0,
            "vocal_quality": row.get("vocal_quality", {}).get("score", 0) if isinstance(row.get("vocal_quality"), dict) else 0,
            "musicality": row.get("musicality", {}).get("score", 0) if isinstance(row.get("musicality"), dict) else 0,
            "boldness": row.get("boldness", {}).get("score", 0) if isinstance(row.get("boldness"), dict) else 0,
            "eye_contact": row.get("eye_contact", {}).get("score") if isinstance(row.get("eye_contact"), dict) else None,
            "body_language": row.get("body_language", {}).get("score") if isinstance(row.get("body_language"), dict) else None,
        })

    return progress
