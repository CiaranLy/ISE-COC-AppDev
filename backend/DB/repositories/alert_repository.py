"""Alert repository."""

from typing import List

from sqlalchemy import select, update

from DB.models.alert import Alert
from DB.repositories.base import AsyncRepository


class AlertRepository(AsyncRepository[Alert]):
    model_cls = Alert

    async def get_pending(self, collector_name: str) -> List[Alert]:
        query = select(Alert).where(
            Alert.collector_name == collector_name,
            Alert.acknowledged == False,
        )
        result = await self.async_session.execute(query)
        return list(result.scalars().all())

    async def acknowledge(self, alert_id: int) -> bool:
        query = (
            update(Alert)
            .where(Alert.id == alert_id)
            .values(acknowledged=True)
        )
        result = await self.async_session.execute(query)
        return result.rowcount > 0
