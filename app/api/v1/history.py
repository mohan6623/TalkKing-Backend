"""History routes — GET /history (protected, paginated)."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """Get paginated session history for the authenticated user."""
    user_id = current_user.get("sub")
    offset = (page - 1) * limit

    supabase = get_supabase()

    # Query sessions with pagination
    result = await asyncio.to_thread(
        lambda: supabase.table("sessions").select(
            "id, type, prompt_type, prompt, duration, status, created_at"
        ).eq("user_id", user_id).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
    )

    # Get total count for pagination metadata
    count_result = await asyncio.to_thread(
        lambda: supabase.table("sessions").select(
            "id", count="exact"
        ).eq("user_id", user_id).execute()
    )
    total = count_result.count if count_result.count else 0

    return {
        "sessions": result.data or [],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0,
        },
    }
