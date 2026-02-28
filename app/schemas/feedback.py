"""Feedback report schemas — mirrors FeedbackReport and sub-schemas from index.ts."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ClarityFeedback(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    score: int
    filler_words: list[dict] = []   # [{word, count}]
    wpm: int
    feedback: str


class VocalQualityFeedback(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    score: int
    breathing: str
    vocal_fry: bool
    raspiness: bool
    feedback: str


class MusicalityFeedback(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    score: int
    pitch_variation: str
    monotone: bool
    feedback: str


class BoldnessFeedback(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    score: int
    weak_phrases: list[dict] = []   # [{phrase, count}]
    feedback: str


class EyeContactFeedback(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    score: int
    gaze_stability: str
    camera_ratio: float
    feedback: str


class BodyLanguageFeedback(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    score: int
    posture: str
    nervous_gestures: list[str] = []
    feedback: str


class FeedbackReport(BaseModel):
    """Complete feedback report for a recording session (6 dimensions)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    session_id: str
    overall_score: int
    clarity: ClarityFeedback
    vocal_quality: VocalQualityFeedback
    musicality: MusicalityFeedback
    boldness: BoldnessFeedback
    eye_contact: Optional[EyeContactFeedback] = None
    body_language: Optional[BodyLanguageFeedback] = None
    improvements: list[str] = []
    strengths: list[str] = []
    next_level_recommendation: str = ""
    personalized_tips: list[str] = []
    recommended_layer: int = 1
