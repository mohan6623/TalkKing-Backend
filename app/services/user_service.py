"""User service — profile CRUD operations via Supabase."""
from __future__ import annotations

import asyncio
from typing import Any
from app.core.supabase_client import get_supabase


async def get_user_profile(user_id: str) -> dict | None:
    """Fetch a user profile from Supabase by ID.

    Args:
        user_id: The Supabase auth user ID (UUID)

    Returns:
        Profile dict or None if not found
    """
    supabase = get_supabase()
    result = await asyncio.to_thread(
        lambda: supabase.table("profiles").select("*").eq("id", user_id).execute()
    )
    if result.data:
        return result.data[0]
    return None


async def update_user_profile(user_id: str, updates: dict[str, Any]) -> dict | None:
    """Update a user profile in Supabase.

    Args:
        user_id: The Supabase auth user ID
        updates: Dict of fields to update

    Returns:
        Updated profile dict or None
    """
    # Only allow safe fields to be updated
    allowed_fields = {"name", "avatar", "mission", "weakness"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}

    if not safe_updates:
        return await get_user_profile(user_id)

    supabase = get_supabase()
    result = await asyncio.to_thread(
        lambda: supabase.table("profiles").update(safe_updates).eq("id", user_id).execute()
    )
    if result.data:
        return result.data[0]
    return None


async def increment_session_count(user_id: str) -> None:
    """Increment the user's total_sessions counter."""
    supabase = get_supabase()
    await asyncio.to_thread(
        lambda: supabase.rpc("increment_sessions", {"user_id_input": user_id}).execute()
    )


async def update_best_score(user_id: str, score: int) -> None:
    """Update the user's best_score if the new score is higher."""
    profile = await get_user_profile(user_id)
    if profile and score > profile.get("best_score", 0):
        supabase = get_supabase()
        await asyncio.to_thread(
            lambda: supabase.table("profiles").update(
                {"best_score": score}
            ).eq("id", user_id).execute()
        )
