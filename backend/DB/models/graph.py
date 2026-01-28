"""Graph model."""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from DB.models.base import Base


class Graph(Base):
    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collector_id = Column(Integer, ForeignKey("collectors.id", ondelete="CASCADE"), nullable=False)
    unit = Column(String(50), nullable=False)

    collector = relationship("Collector", back_populates="graphs")
    data_points = relationship("Data", back_populates="graph", cascade="all, delete-orphan")
