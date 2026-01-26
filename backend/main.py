from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from config import API_TITLE, API_VERSION
from DB.database import get_async_session, init_db
from DB.repositories import CollectorRepository, DataRepository, GraphTypeRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Data Collector API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# GraphType Endpoints
@app.post("/create_graph_type")
async def create_graph_type(
    name: str, unit: str, session: AsyncSession = Depends(get_async_session)
):
    repo = GraphTypeRepository(session)
    existing = await repo.find_by_name(name)
    if existing:
        return {"id": existing.id, "name": existing.name, "unit": existing.unit}
    
    graph_type = await repo.create(name=name, unit=unit)
    return {"id": graph_type.id, "name": graph_type.name, "unit": graph_type.unit}


@app.get("/graph_types")
async def graph_types(session: AsyncSession = Depends(get_async_session)):
    repo = GraphTypeRepository(session)
    types = await repo.get_all()
    return [{"id": t.id, "name": t.name, "unit": t.unit} for t in types]


# Collector Endpoints
@app.post("/create_collector")
async def create_collector(
    display_name: str, session: AsyncSession = Depends(get_async_session)
):
    repo = CollectorRepository(session)
    existing = await repo.find_by_display_name(display_name)
    if existing:
        return {"id": existing.id, "display_name": existing.display_name}
    
    collector = await repo.create(display_name=display_name)
    return {"id": collector.id, "display_name": collector.display_name}


@app.get("/collectors")
async def collectors(session: AsyncSession = Depends(get_async_session)):
    repo = CollectorRepository(session)
    collectors = await repo.get_all()
    return [{"id": c.id, "display_name": c.display_name} for c in collectors]


@app.get("/collector/{collector_id}")
async def collector(collector_id: int, session: AsyncSession = Depends(get_async_session)):
    repo = CollectorRepository(session)
    collector = await repo.get_by_id(collector_id)
    if not collector:
        return {"error": "Collector not found"}
    return {"id": collector.id, "display_name": collector.display_name}


# Data Endpoints
@app.post("/create_data")
async def create_data(
    collector_id: int,
    graph_type_id: int,
    content: float,
    session: AsyncSession = Depends(get_async_session),
):
    repo = DataRepository(session)
    data = await repo.create(collector_id=collector_id, graph_type_id=graph_type_id, content=content)
    return {
        "id": data.id,
        "collector_id": data.collector_id,
        "graph_type_id": data.graph_type_id,
        "timestamp_utc": data.timestamp_utc,
        "content": data.content,
    }


@app.get("/data")
async def data(
    collector_id: int,
    graph_type_id: int | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    repo = DataRepository(session)
    data = await repo.find_by_collector(collector_id, graph_type_id, limit)
    return [
        {
            "id": d.id,
            "graph_type_id": d.graph_type_id,
            "timestamp_utc": d.timestamp_utc,
            "content": d.content,
        }
        for d in data
    ]
