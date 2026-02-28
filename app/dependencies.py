"""Shared FastAPI dependencies (DI) — Supabase client, auth, etc."""
from fastapi import Depends
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase

# Re-export for convenient imports in route modules
__all__ = ["get_current_user", "get_supabase"]
