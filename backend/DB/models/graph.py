"""Graph model."""

from sqlalchemy import Column, Float, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from DB.models.base import Base


class Graph(Base):
    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collector_id = Column(Integer, ForeignKey("collectors.id", ondelete="CASCADE"), nullable=False)
    unit = Column(String(50), nullable=False)
    session_id = Column(String(255), nullable=False, index=True)
    max_value = Column(Float, nullable=True)
    time_created = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    collector = relationship("Collector", back_populates="graphs")
    data_points = relationship("Data", back_populates="graph", cascade="all, delete-orphan")
