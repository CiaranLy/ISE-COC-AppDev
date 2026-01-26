"""GraphType model."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from DB.models.base import Base


class GraphType(Base):
    __tablename__ = "graph_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    unit = Column(String(50), nullable=False)

    data_points = relationship("Data", back_populates="graph_type", cascade="all, delete-orphan")
