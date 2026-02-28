"""Auth routes — POST /auth/signup, POST /auth/login (public endpoints)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

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
    """Register a new user via Supabase Auth.

    Implementation will call supabase.auth.sign_up() in a later task.
    """
    # TODO: Implement with Supabase Auth (Task 10)
    raise HTTPException(status_code=501, detail="Signup not yet implemented")


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Login an existing user via Supabase Auth.

    Implementation will call supabase.auth.sign_in_with_password() in a later task.
    """
    # TODO: Implement with Supabase Auth (Task 10)
    raise HTTPException(status_code=501, detail="Login not yet implemented")
