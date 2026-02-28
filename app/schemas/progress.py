"""Progress data schema — mirrors ProgressData from index.ts."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ProgressData(BaseModel):
    """A single data point for the progress chart."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    date: str
    overall_score: int
    clarity: int
    vocal_quality: int
    musicality: int
    boldness: int
    eye_contact: Optional[int] = None
    body_language: Optional[int] = None
