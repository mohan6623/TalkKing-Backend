"""Supabase client singleton — connects to managed Supabase PostgreSQL + Auth."""
from __future__ import annotations

from functools import lru_cache
from supabase import create_client, Client
from app.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a cached Supabase client instance.

    Uses the service-role key so backend can bypass RLS for admin operations.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    """Return a cached Supabase client using the anon key.

    Used for auth operations (signup/login) where RLS should apply.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
