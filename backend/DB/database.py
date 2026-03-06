"""Database configuration."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import DATABASE_URL, DB_ECHO
from DB.models.base import Base
from log_config import get_logger

logger = get_logger("database")

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL, echo=DB_ECHO, poolclass=NullPool
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error("Session rollback due to error: %s", e)
            await session.rollback()
            raise


async def init_db() -> None:
    logger.info("Initializing database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
