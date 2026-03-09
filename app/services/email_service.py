"""Mailgun email service — sends feedback notification emails via Student Pack free tier."""
from __future__ import annotations

import httpx
from app.config import settings


async def send_feedback_email(
    to_email: str,
    user_name: str,
    overall_score: int,
    top_strength: str,
    top_improvement: str,
) -> None:
    """Send a feedback summary email via Mailgun (Student Pack — 20K/mo free).

    Args:
        to_email: Recipient email address
        user_name: User's display name
        overall_score: Overall session score (0-100)
        top_strength: User's best dimension this session
        top_improvement: Area most needing work
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
            auth=("api", settings.MAILGUN_API_KEY),
            data={
                "from": f"TalkKing <noreply@{settings.MAILGUN_DOMAIN}>",
                "to": to_email,
                "subject": f"Your TalkKing Score: {overall_score}/100 🎯",
                "html": f"""
                    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                        <h2 style="color: #6366f1;">Hey {user_name}! 🎤</h2>
                        <p>Your latest practice session scored <strong style="font-size: 1.5em; color: #6366f1;">{overall_score}/100</strong>.</p>
                        <div style="background: #f1f5f9; border-radius: 12px; padding: 16px; margin: 16px 0;">
                            <p style="margin: 4px 0;">💪 <strong>Strength:</strong> {top_strength}</p>
                            <p style="margin: 4px 0;">📈 <strong>Focus area:</strong> {top_improvement}</p>
                        </div>
                        <a href="https://talkking.me/dashboard"
                           style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                            View full report →
                        </a>
                        <p style="color: #94a3b8; font-size: 0.85em; margin-top: 24px;">
                            Keep speaking boldly! — The TalkKing Team
                        </p>
                    </div>
                """,
            },
        )
        response.raise_for_status()
