"""GraphType repository."""

from typing import Optional

from sqlalchemy import select

from ..models.graph_type import GraphType
from .base import AsyncRepository


class GraphTypeRepository(AsyncRepository[GraphType]):
    model_cls = GraphType

    async def find_by_name(self, name: str) -> Optional[GraphType]:
        query = select(GraphType).where(GraphType.name == name)
        result = await self.async_session.execute(query)
        return result.scalars().first()
