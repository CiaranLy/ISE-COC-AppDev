"""Database setup."""

import asyncio
from DB.database import async_engine, init_db
from DB.models.base import Base
from log_config import get_logger

logger = get_logger("setup_db")


async def setup():
    logger.info("Creating database...")
    await init_db()

    async with async_engine.connect() as conn:
        tables = list(Base.metadata.tables.keys())
        logger.info("Created tables: %s", ", ".join(tables))

    logger.info("Start FastAPI server: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(setup())
