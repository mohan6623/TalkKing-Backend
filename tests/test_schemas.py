"""Tests for Pydantic v2 schemas — mirrors src/types/index.ts."""
from app.schemas.user import UserProfile, MissionType, WeaknessType
from app.schemas.session import RecordingSession
from app.schemas.feedback import (
    FeedbackReport,
    ClarityFeedback,
    VocalQualityFeedback,
    MusicalityFeedback,
    BoldnessFeedback,
    EyeContactFeedback,
    BodyLanguageFeedback,
)
from app.schemas.progress import ProgressData
from app.schemas.achievement import Achievement
from app.schemas.assessment import DemoAssessmentResult, DemoSkillScores, DemoTeaserData, DemoSkillSuggestion


# ── UserProfile ──────────────────────────────────────────────────────

def test_user_profile_valid():
    user = UserProfile(
        id="uuid-123",
        name="Test User",
        email="test@test.com",
        avatar="",
        mission="tech-interview",
        weakness="filler-words",
        current_level=1,
        total_sessions=0,
        streak_days=0,
        best_score=0,
        average_wpm=0.0,
    )
    assert user.name == "Test User"
    assert user.mission == "tech-interview"


def test_user_profile_all_missions():
    for m in ("tech-interview", "sales-pitch", "conflict-resolution", "storytelling", "dating"):
        user = UserProfile(
            id="u1", name="A", email="a@b.com", avatar="",
            mission=m, weakness="filler-words",
            current_level=1, total_sessions=0, streak_days=0,
            best_score=0, average_wpm=0.0,
        )
        assert user.mission == m


def test_user_profile_all_weaknesses():
    for w in ("filler-words", "sound-nervous", "monotone", "weak-language", "eye-contact", "body-language"):
        user = UserProfile(
            id="u1", name="A", email="a@b.com", avatar="",
            mission="tech-interview", weakness=w,
            current_level=1, total_sessions=0, streak_days=0,
            best_score=0, average_wpm=0.0,
        )
        assert user.weakness == w


# ── RecordingSession ─────────────────────────────────────────────────

def test_recording_session_audio():
    s = RecordingSession(
        id="s-1", type="audio", prompt_type="random",
        prompt="Tell me about yourself", duration=300,
    )
    assert s.type == "audio"
    assert s.duration == 300


def test_recording_session_video():
    s = RecordingSession(
        id="s-2", type="video", prompt_type="free-flow",
        prompt="", duration=120,
    )
    assert s.type == "video"


# ── FeedbackReport ───────────────────────────────────────────────────

def test_feedback_report_audio_only():
    """Audio-only sessions: eye_contact and body_language are None."""
    fb = FeedbackReport(
        session_id="s-1",
        overall_score=78,
        clarity=ClarityFeedback(score=80, filler_words=[], wpm=130, feedback="Good clarity"),
        vocal_quality=VocalQualityFeedback(score=75, breathing="normal", vocal_fry=False, raspiness=False, feedback="Ok"),
        musicality=MusicalityFeedback(score=70, pitch_variation="good", monotone=False, feedback="Decent pitch"),
        boldness=BoldnessFeedback(score=85, weak_phrases=[], feedback="Strong language"),
        improvements=["Reduce filler words"],
        strengths=["Good pacing"],
        next_level_recommendation="Try harder topics",
        personalized_tips=["Practice pausing"],
        recommended_layer=2,
    )
    assert fb.overall_score == 78
    assert fb.eye_contact is None
    assert fb.body_language is None


def test_feedback_report_video():
    """Video sessions include eye_contact and body_language."""
    fb = FeedbackReport(
        session_id="s-2",
        overall_score=82,
        clarity=ClarityFeedback(score=85, filler_words=[{"word": "um", "count": 3}], wpm=140, feedback="Clear"),
        vocal_quality=VocalQualityFeedback(score=78, breathing="deep", vocal_fry=False, raspiness=False, feedback="Good"),
        musicality=MusicalityFeedback(score=72, pitch_variation="moderate", monotone=False, feedback="Ok"),
        boldness=BoldnessFeedback(score=88, weak_phrases=[], feedback="Bold"),
        eye_contact=EyeContactFeedback(score=90, gaze_stability="stable", camera_ratio=0.85, feedback="Great"),
        body_language=BodyLanguageFeedback(score=70, posture="upright", nervous_gestures=["hair touching"], feedback="Watch gestures"),
        improvements=["Reduce nervous gestures"],
        strengths=["Eye contact", "Boldness"],
        next_level_recommendation="Master musicality",
        personalized_tips=["Vary pitch more"],
        recommended_layer=3,
    )
    assert fb.eye_contact.score == 90
    assert fb.body_language.nervous_gestures == ["hair touching"]


# ── ProgressData ─────────────────────────────────────────────────────

def test_progress_data():
    p = ProgressData(
        date="2026-02-28",
        overall_score=75,
        clarity=80,
        vocal_quality=70,
        musicality=65,
        boldness=85,
    )
    assert p.overall_score == 75
    assert p.eye_contact is None


# ── Achievement ──────────────────────────────────────────────────────

def test_achievement():
    a = Achievement(
        id="a-1",
        name="First Session",
        description="Complete your first session",
        icon="🎯",
        unlocked_at="2026-02-28T10:00:00Z",
        category="milestone",
    )
    assert a.category == "milestone"


def test_achievement_locked():
    a = Achievement(
        id="a-2",
        name="Streak Master",
        description="7-day streak",
        icon="🔥",
        unlocked_at=None,
        category="streak",
    )
    assert a.unlocked_at is None


# ── Demo Assessment ──────────────────────────────────────────────────

def test_demo_skill_scores():
    scores = DemoSkillScores(clarity=7, vocal=8, musicality=6, boldness=9)
    assert scores.clarity == 7
    assert scores.boldness == 9


def test_demo_assessment_result():
    result = DemoAssessmentResult(
        id="demo-1",
        duration=120,
        recorded_at="2026-02-28T10:00:00Z",
        scores=DemoSkillScores(clarity=7, vocal=8, musicality=6, boldness=9),
        overall_score=7,
        overall_level="intermediate",
        feedback="Great start!",
        suggestions=[
            DemoSkillSuggestion(dimension="Musicality", score=6, tip="Vary your pitch", layer_link=3),
        ],
        filler_words=[{"word": "um", "count": 5}],
        weak_phrases=[],
        wpm=130,
        recommended_layer=2,
        teaser_data=DemoTeaserData(
            overall_score=7,
            highlights=["Your Boldness is strong!"],
            top_dimension="Boldness",
        ),
    )
    assert result.overall_level == "intermediate"
    assert len(result.suggestions) == 1
