"""Database setup."""

import asyncio
import sys
from DB.database import async_engine, init_db
from DB.repositories import GraphTypeRepository
from DB.database import AsyncSessionLocal
from sqlalchemy import text

async def setup():

    print("Creating database...")
    await init_db()
    
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [r[0] for r in result.fetchall()]
        print(f"✓ Created tables: {', '.join(tables)}")

    # Seed GraphTypes
    print("\nSeeding GraphTypes...")
    async with AsyncSessionLocal() as session:
        repo = GraphTypeRepository(session)
        
        # CPU
        cpu = await repo.find_by_name("CPU Usage")
        if not cpu:
            cpu = await repo.create(name="CPU Usage", unit="%")
            
        # RAM
        ram = await repo.find_by_name("RAM Usage")
        if not ram:
            ram = await repo.create(name="RAM Usage", unit="MB")
            
        # Temp
        temp = await repo.find_by_name("Temperature")
        if not temp:
            temp = await repo.create(name="Temperature", unit="°C")
            
        await session.commit()
        print(f"✓ Seeded: {cpu.name}, {ram.name}, {temp.name}")
    
    print("\nStart FastAPI server: uvicorn main:app --reload")

if __name__ == "__main__":
    asyncio.run(setup())
