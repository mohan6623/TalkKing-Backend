"""Google Gemini boldness/logic analysis service — analyzes transcript for confident language."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
import httpx
from app.config import settings


@dataclass
class BoldnessResult:
    """Result from Gemini boldness analysis."""
    score: int = 0                                    # 0-100
    weak_phrases: list[dict] = field(default_factory=list)  # [{phrase, count}]
    feedback: str = ""


BOLDNESS_PROMPT = """You are an expert communication coach analyzing a speech transcript.
Analyze the following transcript for BOLDNESS — the speaker's use of confident, decisive language.

Mission context: The speaker is practicing for "{mission}".

Transcript:
\"\"\"
{transcript}
\"\"\"

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "score": <integer 0-100>,
  "weak_phrases": [
    {{"phrase": "<hedging/weak phrase found>", "count": <number of occurrences>}}
  ],
  "feedback": "<2-3 sentence feedback on their boldness and language confidence>"
}}

Score guide:
- 90-100: Extremely bold and decisive language
- 70-89: Generally confident with minor hedging
- 50-69: Mixed — some bold statements but frequent hedging
- 30-49: Mostly weak/uncertain language
- 0-29: Very timid, constant hedging and qualifiers"""


async def analyze_boldness(transcript: str, mission: str) -> BoldnessResult:
    """Send transcript to Gemini 1.5 Flash for boldness analysis.

    Args:
        transcript: The speech transcript text
        mission: User's mission type for context

    Returns:
        BoldnessResult with score, weak phrases, and feedback
    """
    if not transcript.strip():
        return BoldnessResult(score=0, feedback="No speech detected.")

    prompt = BOLDNESS_PROMPT.format(transcript=transcript, mission=mission)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 500,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

    # Extract JSON from Gemini response
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    # Parse — strip any markdown code fences if present
    clean = raw_text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]  # remove first line
        clean = clean.rsplit("```", 1)[0]  # remove last fence

    parsed = json.loads(clean)

    return BoldnessResult(
        score=parsed.get("score", 0),
        weak_phrases=parsed.get("weak_phrases", []),
        feedback=parsed.get("feedback", ""),
    )
