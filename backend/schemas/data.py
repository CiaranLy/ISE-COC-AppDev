"""Pydantic schemas for Data."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DataBase(BaseModel):
    content: float

    model_config = ConfigDict(from_attributes=True)


class DataCreate(DataBase):
    collector_id: int
    graph_type_id: int


class DataRead(DataBase):
    id: int
    collector_id: int
    graph_type_id: int
    timestamp_utc: datetime
