"""Celery task: process_recording — AI analysis pipeline for audio recordings."""
from __future__ import annotations

import asyncio
import base64
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.analysis.process_recording",
    max_retries=2,
    soft_time_limit=120,
    time_limit=150,
    acks_late=True,
)
def process_recording(
    self,
    audio_b64: str,
    user_mission: str,
    session_id: str,
    user_id: str | None = None,
    user_email: str | None = None,
    user_name: str | None = None,
    duration_seconds: float = 300.0,
):
    """Celery task: run full AI analysis pipeline and store results.

    Flow:
        1. Run AI orchestrator (Groq + Hume parallel, then Gemini)
        2. Store feedback report in Supabase
        3. Update session status to 'completed'
        4. Send email notification via Mailgun (optional)

    Args:
        audio_b64: Base64-encoded audio bytes (JSON-safe)
        user_mission: User's mission type for context
        session_id: The recording session ID
        user_id: The authenticated user's ID
        user_email: Optional email for notification
        user_name: Optional name for email personalization
    """
    try:
        async def _run_pipeline():
            """Async pipeline: AI analysis → store → email."""
            audio_data = base64.b64decode(audio_b64)

            from app.services.ai_orchestrator import analyze_recording
            feedback = await analyze_recording(
                audio_data, user_mission, session_id, duration_seconds=duration_seconds
            )

            if user_id:
                feedback["user_id"] = user_id

            try:
                from app.core.supabase_client import get_supabase
                supabase = get_supabase()
                supabase.table("feedback_reports").insert(feedback).execute()
                supabase.table("sessions").update(
                    {"status": "completed"}
                ).eq("id", session_id).execute()
            except Exception as db_err:
                logger.warning(f"Supabase storage failed (non-fatal): {db_err}")

            if user_email:
                try:
                    from app.services.email_service import send_feedback_email
                    await send_feedback_email(
                        to_email=user_email,
                        user_name=user_name or "there",
                        overall_score=feedback["overall_score"],
                        top_strength=feedback["strengths"][0] if feedback["strengths"] else "Keep practicing!",
                        top_improvement=feedback["improvements"][0] if feedback["improvements"] else "You're doing great!",
                    )
                except Exception as email_err:
                    logger.warning(f"Email notification failed (non-fatal): {email_err}")

            return feedback

        asyncio.run(_run_pipeline())
        return {"status": "completed", "session_id": session_id}

    except Exception as exc:
        # Mark session as failed in Supabase
        try:
            from app.core.supabase_client import get_supabase
            supabase = get_supabase()
            supabase.table("sessions").update(
                {"status": "failed", "error": str(exc)}
            ).eq("id", session_id).execute()
        except Exception:
            pass

        logger.error(f"Recording analysis failed: {exc}")
        raise self.retry(exc=exc, countdown=30)
