"""Pydantic schemas for GraphType."""

from pydantic import BaseModel, ConfigDict


class GraphTypeBase(BaseModel):
    name: str
    unit: str

    model_config = ConfigDict(from_attributes=True)


class GraphTypeCreate(GraphTypeBase):
    pass


class GraphTypeRead(GraphTypeBase):
    id: int
