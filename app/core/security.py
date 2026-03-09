"""JWT security — validates Supabase-issued JWTs for protected endpoints."""
from __future__ import annotations

import logging
from typing import Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Validate Supabase JWT locally using SUPABASE_JWT_SECRET.

    Local validation avoids a network round-trip to Supabase Auth on every
    protected request, preventing the timeout-induced 401 errors that occur
    when supabase.auth.get_user() is called remotely per-request.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase tokens use non-standard audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired — please log in again",
        )
    except jwt.InvalidTokenError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    except Exception as e:
        logger.warning("JWT validation unexpected error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
