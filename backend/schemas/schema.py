"""Pydantic schema for data ingestion."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DataIngest(BaseModel):
    """Schema for incoming data from collectors."""
    collector_name: str
    content: float
    unit: str
    timestamp: datetime
    session_id: str
    message_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DataIngestResponse(BaseModel):
    """Response schema for data ingestion."""
    success: bool
    collector_id: int
    graph_id: int
    data_id: int
    session_id: str
    message: str
    message_id: Optional[str] = None  # Echo back for acknowledgment
    acknowledged: bool = True  # Confirms receipt

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Structured error response returned for all server-side failures."""
    success: bool = False
    error: str
    detail: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DataPoint(BaseModel):
    """Schema for individual data points."""
    id: int
    content: float
    timestamp_utc: datetime
    collector_id: int
    session_id: str

    model_config = ConfigDict(from_attributes=True)



class GraphWithDataResponse(BaseModel):
    """Response schema for graphs with data points."""
    id: int
    collector_id: int
    unit: str
    session_id: str
    data_points: List[DataPoint]
    collector_name: str

    model_config = ConfigDict(from_attributes=True)
