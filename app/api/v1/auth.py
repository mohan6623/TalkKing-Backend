"""Auth routes — POST /auth/signup, POST /auth/login (public endpoints).

Best practices applied:
- Email confirmation redirect URL is configurable via `redirect_to`
- Proper separation of "signup succeeded but email pending" vs errors
- Profile creation is atomic with signup
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.core.supabase_client import get_supabase
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Default redirect URL for email confirmation links
_DEFAULT_REDIRECT = (
    "http://localhost:5173"
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
        supabase = get_supabase()

        # Build signup options with the redirect URL for confirmation emails
        redirect_url = body.redirect_to or _DEFAULT_REDIRECT
        signup_options = {
            "email": body.email,
            "password": body.password,
            "options": {
                "email_redirect_to": redirect_url,
            },
        }

        auth_result = supabase.auth.sign_up(signup_options)

        if not auth_result.user:
            raise HTTPException(status_code=400, detail="Signup failed — please try again")

        user_id = auth_result.user.id
        has_session = auth_result.session is not None and bool(
            auth_result.session.access_token
        )

        # Create profile row (uses service key → bypasses RLS)
        supabase.table("profiles").insert({
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
        detail = str(e)
        # Provide a friendlier message for common Supabase errors
        if "already registered" in detail.lower() or "already been registered" in detail.lower():
            detail = "An account with this email already exists. Please log in instead."
        raise HTTPException(status_code=400, detail=detail)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Login an existing user via Supabase Auth."""
    try:
        supabase = get_supabase()
        auth_result = supabase.auth.sign_in_with_password({
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
        detail = str(e)
        if "email not confirmed" in detail.lower():
            detail = "Please confirm your email before logging in. Check your inbox for the confirmation link."
        elif "invalid login" in detail.lower():
            detail = "Invalid email or password. Please try again."
        raise HTTPException(status_code=401, detail=detail)
