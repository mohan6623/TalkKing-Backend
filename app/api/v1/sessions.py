"""Session routes — POST /sessions, POST /sessions/{id}/analyze, GET /sessions/{id}/status (protected)."""
import asyncio
import uuid
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Literal
from app.core.security import get_current_user
from app.core.supabase_client import get_supabase
from app.core.exceptions import AudioTooLargeError
from app.services.audio_utils import validate_audio_size

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
    """Create a new recording session record in Supabase."""
    user_id = current_user.get("sub")
    session_id = str(uuid.uuid4())

    supabase = get_supabase()
    await asyncio.to_thread(
        lambda: supabase.table("sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "type": body.type,
            "prompt_type": body.prompt_type,
            "prompt": body.prompt,
            "duration": body.duration,
            "status": "created",
        }).execute()
    )

    return CreateSessionResponse(session_id=session_id, status="created")


@router.post("/{session_id}/analyze", response_model=AnalyzeResponse)
async def analyze_session(
    session_id: str,
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload audio and enqueue AI analysis via Celery."""
    audio_bytes = await audio.read()

    # Validate audio size
    if not validate_audio_size(audio_bytes):
        raise AudioTooLargeError()

    # Get user profile for mission context and email
    user_id = current_user.get("sub")
    supabase = get_supabase()

    # Verify session ownership
    session_result = await asyncio.to_thread(
        lambda: supabase.table("sessions").select("id, duration").eq("id", session_id).eq("user_id", user_id).execute()
    )
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    session_duration = float(session_result.data[0].get("duration", 300))

    profile_result = await asyncio.to_thread(
        lambda: supabase.table("profiles").select("mission, email, name").eq("id", user_id).execute()
    )
    profile = profile_result.data[0] if profile_result.data else {}

    # Update session status to processing
    await asyncio.to_thread(
        lambda: supabase.table("sessions").update({"status": "processing"}).eq("id", session_id).eq("user_id", user_id).execute()
    )

    # Enqueue Celery task
    from app.tasks.analysis import process_recording
    task = process_recording.delay(
        audio_b64=base64.b64encode(audio_bytes).decode("ascii"),
        user_mission=profile.get("mission", "tech-interview"),
        session_id=session_id,
        user_id=user_id,
        user_email=profile.get("email"),
        user_name=profile.get("name"),
        duration_seconds=session_duration,
    )

    return AnalyzeResponse(
        task_id=task.id,
        status="processing",
        message="Analysis started. Check /sessions/{id}/status for updates.",
    )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Check the processing status of a session's AI analysis."""
    user_id = current_user.get("sub")
    supabase = get_supabase()
    result = await asyncio.to_thread(
        lambda: supabase.table("sessions").select("id, status, error").eq("id", session_id).eq("user_id", user_id).execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = result.data[0]
    return SessionStatusResponse(
        session_id=session["id"],
        status=session["status"],
        error=session.get("error"),
    )
