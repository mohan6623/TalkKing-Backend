"""Progress routes — GET /progress (protected)."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("")
async def get_progress(
    current_user: dict = Depends(get_current_user),
):
    """Get historical progress chart data for the authenticated user.

    Implementation will query Supabase feedback_reports table in a later task.
    """
    # TODO: Implement with Supabase query (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")
