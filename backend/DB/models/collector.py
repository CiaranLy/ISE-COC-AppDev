"""Collector model."""

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from DB.models.base import Base


class Collector(Base):
    __tablename__ = "collectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String(255), unique=True, nullable=False)
    time_created = Column(DateTime, server_default=func.now())

    data_points = relationship("Data", back_populates="collector", cascade="all, delete-orphan")
    graphs = relationship("Graph", back_populates="collector", cascade="all, delete-orphan")
