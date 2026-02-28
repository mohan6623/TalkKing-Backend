"""User routes — GET/PATCH /users/me (protected)."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get the authenticated user's profile.

    Implementation will query Supabase profiles table in a later task.
    """
    # TODO: Implement with Supabase query (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.patch("/me")
async def update_my_profile(body: dict, current_user: dict = Depends(get_current_user)):
    """Update the authenticated user's profile.

    Implementation will update Supabase profiles table in a later task.
    """
    # TODO: Implement with Supabase query (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")
