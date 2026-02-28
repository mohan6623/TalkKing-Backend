"""Custom HTTP exceptions for TalkKing API."""
from fastapi import HTTPException


class TalkKingException(HTTPException):
    """Base exception for TalkKing-specific errors."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class AudioTooLargeError(TalkKingException):
    """Raised when uploaded audio exceeds the maximum allowed size."""

    def __init__(self, max_mb: int = 25):
        super().__init__(
            status_code=413,
            detail=f"Audio file too large. Maximum allowed size is {max_mb}MB.",
        )


class AIServiceError(TalkKingException):
    """Raised when an external AI service fails or is unreachable."""

    def __init__(self, service: str, message: str):
        super().__init__(
            status_code=502,
            detail=f"AI service '{service}' error: {message}",
        )


class AnalysisTimeoutError(TalkKingException):
    """Raised when an AI analysis task exceeds the time limit."""

    def __init__(self, session_id: str, timeout_seconds: int = 120):
        super().__init__(
            status_code=504,
            detail=f"Analysis for session '{session_id}' timed out after {timeout_seconds}s.",
        )
