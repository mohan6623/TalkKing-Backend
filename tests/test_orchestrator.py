"""Tests for feedback engine (score calculation) and AI orchestrator (parallel fan-out)."""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.feedback_engine import calculate_scores
from app.services.groq_service import TranscriptResult
from app.services.gemini_service import BoldnessResult
from app.services.hume_service import AcousticsResult


# ── Feedback Engine: Score Calculation ───────────────────────────────

def test_calculate_scores_audio_only():
    """Audio-only session: 4 dimensions (no eye_contact or body_language)."""
    transcript = TranscriptResult(
        text="Hello world",
        filler_words=[{"word": "um", "count": 2}],
        weak_phrases=[],
        wpm=130,
    )
    acoustics = AcousticsResult(
        score=75, breathing="normal", vocal_fry=False, raspiness=False,
        pitch_variation="moderate", monotone=False, feedback="Good",
    )
    boldness = BoldnessResult(
        score=80, weak_phrases=[], feedback="Strong",
    )

    result = calculate_scores(
        session_id="s-1",
        transcript=transcript,
        acoustics=acoustics,
        boldness=boldness,
    )

    assert "session_id" in result
    assert result["session_id"] == "s-1"
    assert 0 <= result["overall_score"] <= 100
    assert "clarity" in result
    assert "vocal_quality" in result
    assert "musicality" in result
    assert "boldness" in result
    assert result["eye_contact"] is None
    assert result["body_language"] is None
    assert isinstance(result["improvements"], list)
    assert isinstance(result["strengths"], list)


def test_calculate_scores_high_filler_words():
    """Many filler words should reduce the clarity score."""
    transcript = TranscriptResult(
        text="um like you know um basically um",
        filler_words=[{"word": "um", "count": 3}, {"word": "like", "count": 1}, {"word": "you know", "count": 1}, {"word": "basically", "count": 1}],
        weak_phrases=[],
        wpm=100,
    )
    acoustics = AcousticsResult(score=70, breathing="normal", vocal_fry=False, raspiness=False, pitch_variation="moderate", monotone=False, feedback="Ok")
    boldness = BoldnessResult(score=70, weak_phrases=[], feedback="Ok")

    result = calculate_scores("s-2", transcript, acoustics, boldness)
    # Clarity should be penalized for high filler count
    assert result["clarity"]["score"] < 80


def test_calculate_scores_monotone():
    """Monotone acoustics should result in lower musicality score."""
    transcript = TranscriptResult(text="Hello", filler_words=[], weak_phrases=[], wpm=120)
    acoustics = AcousticsResult(score=40, breathing="normal", vocal_fry=False, raspiness=False, pitch_variation="flat", monotone=True, feedback="Monotone")
    boldness = BoldnessResult(score=75, weak_phrases=[], feedback="Ok")

    result = calculate_scores("s-3", transcript, acoustics, boldness)
    assert result["musicality"]["monotone"] is True
    assert result["musicality"]["score"] < 60


def test_calculate_scores_generates_tips():
    """Should generate personalized tips and a recommended layer."""
    transcript = TranscriptResult(text="Hello world", filler_words=[], weak_phrases=[], wpm=120)
    acoustics = AcousticsResult(score=80, breathing="normal", vocal_fry=False, raspiness=False, pitch_variation="dynamic", monotone=False, feedback="Great")
    boldness = BoldnessResult(score=90, weak_phrases=[], feedback="Bold")

    result = calculate_scores("s-4", transcript, acoustics, boldness)
    assert isinstance(result["personalized_tips"], list)
    assert isinstance(result["recommended_layer"], int)
    assert result["recommended_layer"] >= 1


# ── AI Orchestrator: Parallel Fan-out ────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_combines_results():
    """Orchestrator should call all 3 AI services and return a combined feedback dict."""
    mock_transcript = TranscriptResult(text="hello world", filler_words=[], weak_phrases=[], wpm=120)
    mock_acoustics = AcousticsResult(score=75, breathing="normal", vocal_fry=False, raspiness=False, pitch_variation="moderate", monotone=False, feedback="Good")
    mock_boldness = BoldnessResult(score=80, weak_phrases=[], feedback="Strong")

    with patch("app.services.ai_orchestrator.transcribe_audio", new_callable=AsyncMock, return_value=mock_transcript) as m_t, \
         patch("app.services.ai_orchestrator.analyze_acoustics", new_callable=AsyncMock, return_value=mock_acoustics) as m_a, \
         patch("app.services.ai_orchestrator.analyze_boldness", new_callable=AsyncMock, return_value=mock_boldness) as m_b:

        from app.services.ai_orchestrator import analyze_recording
        result = await analyze_recording(b"audio-data", "tech-interview", "session-1")

        # Verify all services were called
        m_t.assert_called_once()
        m_a.assert_called_once()
        m_b.assert_called_once()

        # Verify result structure
        assert "overall_score" in result
        assert "session_id" in result
        assert result["session_id"] == "session-1"


@pytest.mark.asyncio
async def test_orchestrator_parallel_execution():
    """Groq and Hume should be called in parallel (Phase 1), Gemini sequentially (Phase 2)."""
    import asyncio
    call_order = []

    async def mock_transcribe(audio):
        call_order.append("groq_start")
        await asyncio.sleep(0.01)
        call_order.append("groq_end")
        return TranscriptResult(text="hello", filler_words=[], weak_phrases=[], wpm=100)

    async def mock_acoustics(audio):
        call_order.append("hume_start")
        await asyncio.sleep(0.01)
        call_order.append("hume_end")
        return AcousticsResult(score=70, breathing="normal", vocal_fry=False, raspiness=False, pitch_variation="moderate", monotone=False, feedback="Ok")

    async def mock_boldness(transcript, mission):
        call_order.append("gemini")
        return BoldnessResult(score=75, weak_phrases=[], feedback="Ok")

    with patch("app.services.ai_orchestrator.transcribe_audio", side_effect=mock_transcribe), \
         patch("app.services.ai_orchestrator.analyze_acoustics", side_effect=mock_acoustics), \
         patch("app.services.ai_orchestrator.analyze_boldness", side_effect=mock_boldness):

        from app.services.ai_orchestrator import analyze_recording
        await analyze_recording(b"audio", "tech-interview", "s-1")

        # Gemini should come after both Groq and Hume
        assert call_order.index("gemini") > call_order.index("groq_start")
        assert call_order.index("gemini") > call_order.index("hume_start")
