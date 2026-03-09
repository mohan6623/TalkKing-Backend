"""Demo / Skill Assessment schemas — mirrors Demo types from index.ts."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DemoSkillScores(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    """Scores returned by the demo assessment (each 1-10)."""
    clarity: int
    vocal: int
    musicality: int
    boldness: int


class DemoTeaserData(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    """Teaser payload shown to anon users before signup."""
    overall_score: int
    highlights: list[str] = []
    top_dimension: str


class DemoSkillSuggestion(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    """Suggestion for a single dimension."""
    dimension: str
    score: int
    tip: str
    layer_link: int


class DemoAssessmentResult(BaseModel):
    """Full assessment result revealed after signup/login."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    duration: int
    recorded_at: str
    scores: DemoSkillScores
    overall_score: int
    overall_level: Literal[
        "beginner", "elementary", "intermediate",
        "upper-intermediate", "advanced", "expert",
    ]
    feedback: str
    suggestions: list[DemoSkillSuggestion] = []
    filler_words: list[dict] = []  # [{word, count}]
    weak_phrases: list[dict] = []  # [{phrase, count}]
    wpm: int
    recommended_layer: int
    teaser_data: DemoTeaserData
