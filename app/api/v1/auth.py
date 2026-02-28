"""Auth routes — POST /auth/signup, POST /auth/login (public endpoints).

Best practices applied:
- Email confirmation redirect URL is configurable via `redirect_to`
- Proper separation of "signup succeeded but email pending" vs errors
- Profile creation is atomic with signup
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.supabase_client import get_supabase, get_supabase_anon
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Default redirect URL for email confirmation links
_DEFAULT_REDIRECT = (
    "http://localhost:5174"
    if settings.ENVIRONMENT == "development"
    else "https://talkking.me"
)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    redirect_to: Optional[str] = None  # Frontend passes its origin URL


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    message: str
    email_confirmed: bool = True


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest):
    """Register a new user via Supabase Auth, then create a profile row.

    If Supabase has email confirmation enabled, the access_token will be
    empty and email_confirmed=false. The frontend should show a "check
    your email" message instead of logging the user in.
    """
    try:
        supabase_anon = get_supabase_anon()

        # Build signup options with the redirect URL for confirmation emails
        redirect_url = body.redirect_to or _DEFAULT_REDIRECT
        signup_options = {
            "email": body.email,
            "password": body.password,
            "options": {
                "email_redirect_to": redirect_url,
            },
        }

        auth_result = supabase_anon.auth.sign_up(signup_options)

        if not auth_result.user:
            raise HTTPException(status_code=400, detail="Signup failed — please try again")

        user_id = auth_result.user.id
        has_session = auth_result.session is not None and bool(
            auth_result.session.access_token
        )

        # Create profile row (uses service key → bypasses RLS)
        supabase_admin = get_supabase()
        try:
            supabase_admin.table("profiles").insert({
                "id": user_id,
                "name": body.name,
                "email": body.email,
                "mission": "tech-interview",
                "weakness": "filler-words",
                "current_level": 1,
                "total_sessions": 0,
                "streak_days": 0,
                "best_score": 0,
                "average_wpm": 0.0,
            }).execute()
        except Exception as profile_err:
            import logging
            logging.getLogger(__name__).error("Profile insert failed, rolling back auth user %s: %s", user_id, profile_err)
            try:
                supabase_admin.auth.admin.delete_user(user_id)
            except Exception as rollback_err:
                logging.getLogger(__name__).critical("ROLLBACK FAILED: orphaned user %s: %s", user_id, rollback_err)
            raise HTTPException(status_code=500, detail="Account setup failed — please try again.")

        return AuthResponse(
            access_token=auth_result.session.access_token if has_session else "",
            user_id=user_id,
            email_confirmed=has_session,
            message=(
                "Account created successfully"
                if has_session
                else "Account created — please check your email to confirm"
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Signup failed: %s", e)
        detail = str(e)
        if "already registered" in detail.lower() or "already been registered" in detail.lower():
            msg = "An account with this email already exists. Please log in instead."
        else:
            msg = "Signup failed — please try again."
        raise HTTPException(status_code=400, detail=msg)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Login an existing user via Supabase Auth."""
    try:
        supabase_anon = get_supabase_anon()
        auth_result = supabase_anon.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })

        if not auth_result.user or not auth_result.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return AuthResponse(
            access_token=auth_result.session.access_token,
            user_id=auth_result.user.id,
            email_confirmed=True,
            message="Login successful",
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Login failed: %s", e)
        detail = str(e)
        if "email not confirmed" in detail.lower():
            msg = "Please confirm your email before logging in. Check your inbox for the confirmation link."
        elif "invalid login" in detail.lower():
            msg = "Invalid email or password. Please try again."
        else:
            msg = "Login failed — please try again."
        raise HTTPException(status_code=401, detail=msg)


@router.get("/oauth/{provider}")
async def oauth_login(provider: str, redirect_to: Optional[str] = None):
    """Initiate OAuth login (e.g. google, github).

    Constructs the Supabase OAuth URL directly (implicit flow) so that
    Supabase redirects back to the frontend with tokens in the URL hash.
    This avoids PKCE code_verifier issues with server-side initiation.
    """
    import urllib.parse

    if provider not in ("google", "github"):
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    # Where Supabase should redirect AFTER OAuth completes (the frontend callback)
    final_redirect = redirect_to or f"{_DEFAULT_REDIRECT}/auth/callback"

    # Build the Supabase OAuth URL directly (implicit flow — returns tokens in hash)
    oauth_url = (
        f"{settings.SUPABASE_URL}/auth/v1/authorize?"
        f"provider={provider}"
        f"&redirect_to={urllib.parse.quote(final_redirect, safe='')}"
    )

    return RedirectResponse(url=oauth_url)


class OAuthCodeExchange(BaseModel):
    code: str


@router.post("/oauth/callback", response_model=AuthResponse)
async def oauth_callback(body: OAuthCodeExchange):
    """Exchange a PKCE authorization code for a session.

    This endpoint is used as a fallback when Supabase sends a `code`
    query parameter instead of tokens in the URL hash.
    """
    try:
        supabase_anon = get_supabase_anon()
        session_response = supabase_anon.auth.exchange_code_for_session(
            {"auth_code": body.code}
        )

        if not session_response.session or not session_response.user:
            raise HTTPException(status_code=401, detail="Code exchange failed — invalid or expired code")

        user = session_response.user
        session = session_response.session

        # Create profile if it doesn't exist (first-time OAuth user)
        try:
            supabase_admin = get_supabase()
            existing = supabase_admin.table("profiles").select("id").eq("id", user.id).execute()
            if not existing.data:
                supabase_admin.table("profiles").insert({
                    "id": user.id,
                    "name": user.user_metadata.get("full_name", user.user_metadata.get("name", "")),
                    "email": user.email,
                    "mission": "tech-interview",
                    "weakness": "filler-words",
                    "current_level": 1,
                    "total_sessions": 0,
                    "streak_days": 0,
                    "best_score": 0,
                    "average_wpm": 0.0,
                }).execute()
        except Exception as profile_err:
            import logging
            logging.getLogger(__name__).warning("OAuth profile upsert failed (non-fatal): %s", profile_err)

        return AuthResponse(
            access_token=session.access_token,
            user_id=user.id,
            email_confirmed=True,
            message="OAuth login successful",
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("OAuth code exchange failed: %s", e)
        raise HTTPException(status_code=401, detail="OAuth login failed — please try again")

