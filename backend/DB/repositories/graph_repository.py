"""Graph repository."""

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from DB.models.graph import Graph
from DB.repositories.base import AsyncRepository


class GraphRepository(AsyncRepository[Graph]):
    model_cls = Graph

    async def find_by_collector_unit_and_session(
        self, collector_id: int, unit: str, session_id: str
    ) -> Optional[Graph]:
        query = select(Graph).where(
            Graph.collector_id == collector_id,
            Graph.unit == unit,
            Graph.session_id == session_id,
        )
        result = await self.async_session.execute(query)
        return result.scalars().first()

    async def update_max_value(self, graph_id: int, max_value) -> bool:
        query = update(Graph).where(Graph.id == graph_id).values(max_value=max_value)
        result = await self.async_session.execute(query)
        return result.rowcount > 0

    async def get_all_with_data(self, limit: int = 1000) -> List[Graph]:
        """Get all graphs with their data points and collector eagerly loaded."""
        query = (
            select(Graph)
            .options(selectinload(Graph.data_points), selectinload(Graph.collector))
            .limit(limit)
        )
        result = await self.async_session.execute(query)
        return list(result.scalars().all())
