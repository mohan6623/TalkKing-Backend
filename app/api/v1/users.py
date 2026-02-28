"""User routes — GET/PATCH /users/me (protected)."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.services.user_service import get_user_profile, update_user_profile
from app.schemas.user import UserProfile, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get the authenticated user's profile from Supabase."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    profile = await get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(body: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    """Update the authenticated user's profile (name, avatar, mission, weakness only)."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    updated = await update_user_profile(user_id, body.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return updated
