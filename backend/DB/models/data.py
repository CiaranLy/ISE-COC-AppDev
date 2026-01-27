"""Data model."""

from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship

from DB.models.base import Base


class Data(Base):
    __tablename__ = "data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collector_id = Column(Integer, ForeignKey("collectors.id", ondelete="CASCADE"), nullable=False)
    graph_id = Column(Integer, ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False)
    timestamp_utc = Column(DateTime, server_default=func.now(), index=True)
    content = Column(Float, nullable=False)

    collector = relationship("Collector", back_populates="data_points")
    graph = relationship("Graph", back_populates="data_points")
