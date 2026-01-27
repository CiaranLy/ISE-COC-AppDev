"""Data repository."""

from typing import List, Optional

from sqlalchemy import desc, select

from DB.models.data import Data
from DB.repositories.base import AsyncRepository


class DataRepository(AsyncRepository[Data]):
    model_cls = Data

    async def find_by_collector_and_graph(
        self, collector_id: int, graph_id: Optional[int] = None, limit: int = 100
    ) -> List[Data]:
        query = select(Data).where(Data.collector_id == collector_id)
        if graph_id is not None:
            query = query.where(Data.graph_id == graph_id)
        query = query.order_by(desc(Data.timestamp_utc)).limit(limit)
        result = await self.async_session.execute(query)
        return list(result.scalars().all())
