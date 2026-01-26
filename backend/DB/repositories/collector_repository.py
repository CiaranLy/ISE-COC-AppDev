"""Collector repository."""

from typing import Optional

from sqlalchemy import select

from DB.models.collector import Collector
from DB.repositories.base import AsyncRepository


class CollectorRepository(AsyncRepository[Collector]):
    model_cls = Collector

    async def find_by_display_name(self, display_name: str) -> Optional[Collector]:
        query = select(Collector).where(Collector.display_name == display_name)
        result = await self.async_session.execute(query)
        return result.scalars().first()
