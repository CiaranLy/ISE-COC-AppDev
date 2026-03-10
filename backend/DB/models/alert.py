"""Alert model."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from DB.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collector_name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
