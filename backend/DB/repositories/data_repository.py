"""Data repository."""

from typing import List, Optional

from sqlalchemy import desc, select

from ..models.data import Data
from .base import AsyncRepository


class DataRepository(AsyncRepository[Data]):
    model_cls = Data

    async def find_by_collector_and_graph_type(
        self, collector_id: int, graph_type_id: Optional[int] = None, limit: int = 100
    ) -> List[Data]:
        query = select(Data).where(Data.collector_id == collector_id)
        if graph_type_id is not None:
            query = query.where(Data.graph_type_id == graph_type_id)
        query = query.order_by(desc(Data.timestamp_utc)).limit(limit)
        result = await self.async_session.execute(query)
        return list(result.scalars().all())
