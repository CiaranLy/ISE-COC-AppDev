"""Base repository."""

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from DB.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class AsyncRepository(Generic[ModelType]):
    model_cls: Type[ModelType]

    def __init__(self, async_session: AsyncSession):
        self.async_session = async_session

    async def create(self, **kwargs) -> ModelType:
        instance = self.model_cls(**kwargs)
        self.async_session.add(instance)
        await self.async_session.flush()
        await self.async_session.refresh(instance)
        return instance

    async def get_by_id(self, record_id: Any) -> Optional[ModelType]:
        return await self.async_session.get(self.model_cls, record_id)

    async def get_all(self, limit: int = 1000) -> List[ModelType]:
        query = select(self.model_cls).limit(limit)
        result = await self.async_session.execute(query)
        return list(result.scalars().all())

    async def delete(self, record_id: Any) -> bool:
        instance = await self.get_by_id(record_id)
        if instance:
            await self.async_session.delete(instance)
            await self.async_session.flush()
            return True
        return False
