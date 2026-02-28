"""History routes — GET /history (protected, paginated)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """Get paginated session history for the authenticated user.

    Implementation will query Supabase sessions + feedback_reports in a later task.
    """
    # TODO: Implement with Supabase query (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")
