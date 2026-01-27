"""Pydantic schema for data ingestion."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DataIngest(BaseModel):
    """Schema for incoming data from collectors."""
    collector_name: str
    content: float
    unit: str
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DataIngestResponse(BaseModel):
    """Response schema for data ingestion."""
    success: bool
    collector_id: int
    graph_type_id: int
    data_id: int
    message: str

    model_config = ConfigDict(from_attributes=True)
