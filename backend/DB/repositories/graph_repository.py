"""Graph repository."""

from typing import Optional

from sqlalchemy import select

from DB.models.graph import Graph
from DB.repositories.base import AsyncRepository


class GraphRepository(AsyncRepository[Graph]):
    model_cls = Graph

   
    async def find_by_name_and_unit(self, name: str, unit: str) -> Optional[Graph]:
        query = select(Graph).where(Graph.name == name, Graph.unit == unit)
        result = await self.async_session.execute(query)
        return result.scalars().first()
