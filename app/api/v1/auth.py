"""Auth routes — POST /auth/signup, POST /auth/login (public endpoints)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str
    message: str


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest):
    """Register a new user via Supabase Auth, then create a profile row."""
    try:
        supabase = get_supabase()
        auth_result = supabase.auth.sign_up({
            "email": body.email,
            "password": body.password,
        })

        if not auth_result.user:
            raise HTTPException(status_code=400, detail="Signup failed")

        user_id = auth_result.user.id

        # Create profile row
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
            access_token=auth_result.session.access_token if auth_result.session else "",
            user_id=user_id,
            message="Account created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            message="Login successful",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
