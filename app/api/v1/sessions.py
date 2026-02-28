"""Session routes — POST /sessions, POST /sessions/{id}/analyze, GET /sessions/{id}/status (protected)."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Literal
from app.core.security import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    type: Literal["video", "audio"]
    prompt_type: Literal["random", "specific", "free-flow"]
    prompt: str = ""
    duration: int


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str
    message: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str  # processing | completed | failed
    error: str | None = None


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new recording session record in Supabase.

    Implementation will insert into sessions table in a later task.
    """
    # TODO: Implement with Supabase (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/{session_id}/analyze", response_model=AnalyzeResponse)
async def analyze_session(
    session_id: str,
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload audio and enqueue AI analysis via Celery.

    Implementation will validate audio, enqueue Celery task in a later task.
    """
    # TODO: Implement with Celery dispatch (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Check the processing status of a session's AI analysis.

    Implementation will query Supabase sessions table in a later task.
    """
    # TODO: Implement with Supabase query (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")
