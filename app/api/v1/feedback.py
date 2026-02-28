"""Feedback routes — GET /sessions/{id}/feedback (protected)."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase
from app.schemas.feedback import FeedbackReport

router = APIRouter(prefix="/sessions", tags=["feedback"])


@router.get("/{session_id}/feedback", response_model=FeedbackReport)
async def get_feedback(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the feedback report for a completed session from Supabase."""
    user_id = current_user.get("sub")
    supabase = get_supabase()
    result = await asyncio.to_thread(
        lambda: supabase.table("feedback_reports").select("*").eq("session_id", session_id).eq("user_id", user_id).execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Feedback not found. Session may still be processing.")

    return result.data[0]
