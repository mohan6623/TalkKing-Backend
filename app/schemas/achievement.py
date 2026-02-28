"""Achievement schema — mirrors Achievement from index.ts."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class Achievement(BaseModel):
    """User achievement / badge."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str
    icon: str
    unlocked_at: Optional[str] = None
    category: Literal["milestone", "skill", "streak"]
