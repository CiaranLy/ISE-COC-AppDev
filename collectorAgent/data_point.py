"""Data point model for the queue."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataPoint:
    """Represents a single data point to be sent to the backend."""
    collector_name: str
    content: float
    unit: str
    timestamp: datetime
    session_id: str

    def to_dict(self) -> dict:
        """Convert to dictionary for API request."""
        ts = self.timestamp
        if hasattr(ts, "isoformat"):
            ts_str = ts.isoformat()
        else:
            from datetime import datetime, timezone
            ts_str = datetime.now(timezone.utc).isoformat()
        return {
            "collector_name": self.collector_name,
            "content": self.content,
            "unit": self.unit,
            "timestamp": ts_str,
            "session_id": self.session_id,
        }
