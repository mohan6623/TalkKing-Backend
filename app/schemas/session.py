"""Recording session schema — mirrors RecordingSession from index.ts."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RecordingSession(BaseModel):
    """A single recording session."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    type: Literal["video", "audio"]
    prompt_type: Literal["random", "specific", "free-flow"]
    prompt: str = ""
    duration: int  # seconds
    recorded_at: Optional[str] = None
    thumbnail: Optional[str] = None
    recording_url: Optional[str] = None
