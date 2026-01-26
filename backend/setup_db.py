"""Database setup."""

import asyncio
import sys
from DB.database import async_engine, init_db
from sqlalchemy import text

async def setup():

    print("Creating database...")
    await init_db()
    
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [r[0] for r in result.fetchall()]
        print(f"✓ Created tables: {', '.join(tables)}")

    print("\nStart FastAPI server: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(setup())
