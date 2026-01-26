"""Pydantic schemas for Collector."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CollectorBase(BaseModel):
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class CollectorCreate(CollectorBase):
    pass


class CollectorRead(CollectorBase):
    id: int
    time_created: Optional[datetime] = None
