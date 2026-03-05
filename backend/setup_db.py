"""Database setup."""

import asyncio
from DB.database import async_engine, init_db
from sqlalchemy import text
from log_config import get_logger

logger = get_logger("setup_db")


async def setup():
    logger.info("Creating database...")
    await init_db()

    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [r[0] for r in result.fetchall()]
        logger.info("Created tables: %s", ", ".join(tables))

    logger.info("Start FastAPI server: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(setup())
