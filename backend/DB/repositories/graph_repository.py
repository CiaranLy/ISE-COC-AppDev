"""Graph repository."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from DB.models.graph import Graph
from DB.repositories.base import AsyncRepository


class GraphRepository(AsyncRepository[Graph]):
    model_cls = Graph

   
    async def find_by_collector_and_unit(self, collector_id: int, unit: str) -> Optional[Graph]:
        query = select(Graph).where(Graph.collector_id == collector_id, Graph.unit == unit)
        result = await self.async_session.execute(query)
        return result.scalars().first()
    
    async def get_all_with_data(self, limit: int = 1000) -> List[Graph]:
        """Get all graphs with their data points and collector info eagerly loaded."""
        query = (
            select(Graph)
            .options(selectinload(Graph.data_points), selectinload(Graph.collector))
            .limit(limit)
        )
        result = await self.async_session.execute(query)
        return list(result.scalars().all())
