"""Tests for core layer — exceptions, supabase client, security."""
from app.core.exceptions import TalkKingException, AudioTooLargeError, AIServiceError, AnalysisTimeoutError


def test_audio_too_large_error():
    exc = AudioTooLargeError(max_mb=25)
    assert exc.status_code == 413
    assert "25" in exc.detail


def test_ai_service_error():
    exc = AIServiceError(service="groq", message="timeout")
    assert exc.status_code == 502
    assert "groq" in exc.detail


def test_analysis_timeout_error():
    exc = AnalysisTimeoutError(session_id="s-1", timeout_seconds=120)
    assert exc.status_code == 504
    assert "120" in exc.detail


def test_base_exception():
    exc = TalkKingException(status_code=500, detail="Internal error")
    assert exc.status_code == 500
