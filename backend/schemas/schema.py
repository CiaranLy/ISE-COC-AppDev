"""Pydantic schema for data ingestion."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class DataIngest(BaseModel):
    """Schema for incoming data from collectors."""
    collector_name: str
    content: float
    unit: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class DataIngestResponse(BaseModel):
    """Response schema for data ingestion."""
    success: bool
    collector_id: int
    graph_id: int
    data_id: int
    message: str

    model_config = ConfigDict(from_attributes=True)


class DataPoint(BaseModel):
    """Schema for individual data points."""
    id: int
    content: float
    timestamp_utc: datetime
    collector_id: int

    model_config = ConfigDict(from_attributes=True)



class GraphWithDataResponse(BaseModel):
    """Response schema for graphs with data points."""
    id: int
    name: str
    unit: str
    data_points: List[DataPoint]

    model_config = ConfigDict(from_attributes=True)
