"""Feedback routes — GET /sessions/{id}/feedback (protected)."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user

router = APIRouter(prefix="/sessions", tags=["feedback"])


@router.get("/{session_id}/feedback")
async def get_feedback(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the feedback report for a completed session.

    Implementation will query Supabase feedback_reports table in a later task.
    """
    # TODO: Implement with Supabase query (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")
