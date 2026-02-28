"""Tests for Mailgun email service."""
import pytest
import respx
import httpx
from app.services.email_service import send_feedback_email


@pytest.mark.asyncio
@respx.mock
async def test_send_feedback_email_success():
    """Should POST to Mailgun API with correct payload."""
    respx.post("https://api.mailgun.net/v3/mail.talkking.me/messages").mock(
        return_value=httpx.Response(200, json={"id": "msg-123", "message": "Queued"})
    )
    await send_feedback_email(
        to_email="user@test.com",
        user_name="Mohan",
        overall_score=85,
        top_strength="Strong Clarity",
        top_improvement="Improve Musicality",
    )
    assert respx.calls.call_count == 1
    content = respx.calls[0].request.content.decode()
    assert "user%40test.com" in content or "user@test.com" in content
    assert "85" in content


@pytest.mark.asyncio
@respx.mock
async def test_send_feedback_email_includes_name():
    """Email body should include the user's name."""
    respx.post("https://api.mailgun.net/v3/mail.talkking.me/messages").mock(
        return_value=httpx.Response(200, json={"id": "msg-456"})
    )
    await send_feedback_email("u@t.com", "TestUser", 70, "Boldness", "Clarity")
    content = respx.calls[0].request.content.decode()
    assert "TestUser" in content
