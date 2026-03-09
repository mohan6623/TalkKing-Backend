"""User-related schemas — mirrors UserProfile, MissionType, WeaknessType from index.ts."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MissionType = Literal[
    "tech-interview",
    "sales-pitch",
    "conflict-resolution",
    "storytelling",
    "dating",
]

WeaknessType = Literal[
    "filler-words",
    "sound-nervous",
    "monotone",
    "weak-language",
    "eye-contact",
    "body-language",
]


class WordCount(BaseModel):
    """Reusable {word, count} pair."""
    word: str
    count: int


class PhraseCount(BaseModel):
    """Reusable {phrase, count} pair."""
    phrase: str
    count: int


class UserProfile(BaseModel):
    """Mirrors the TypeScript UserProfile interface."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    email: str
    avatar: str = ""
    joined_at: Optional[str] = None
    mission: MissionType
    weakness: WeaknessType
    current_level: int = 1
    total_sessions: int = 0
    streak_days: int = 0
    best_score: int = 0
    common_filler_words: list[WordCount] = []
    common_weak_phrases: list[PhraseCount] = []
    average_wpm: float = 0.0
    improvement_areas: list[str] = []
    strengths: list[str] = []


class UserProfileUpdate(BaseModel):
    """Allowed fields for PATCH /users/me."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: Optional[str] = None
    avatar: Optional[str] = None
    mission: Optional[MissionType] = None
    weakness: Optional[WeaknessType] = None
