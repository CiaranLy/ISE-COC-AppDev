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


class SimpleDataPoint(BaseModel):
    """Extremely lightweight schema for massive data arrays, with basic labels."""
    timestamp: float
    value: float

    model_config = ConfigDict(from_attributes=True)


class GraphWithDataResponse(BaseModel):
    """Response schema for graphs with data points."""
    id: int
    collector_id: int
    unit: str
    session_id: str
    data_points: List[SimpleDataPoint]
    collector_name: str
    max_value: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ThresholdUpdate(BaseModel):
    """Request schema for updating a graph's max_value threshold."""
    max_value: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class AlertCreate(BaseModel):
    """Request schema for creating an alert."""
    collector_name: str
    unit: str
    value: float
    threshold: float

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    """Response schema for alerts."""
    id: int
    collector_name: str
    unit: str
    value: float
    threshold: float

    model_config = ConfigDict(from_attributes=True)
