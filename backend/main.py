from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import (
    CollectorCreate,
    CollectorRead,
    DataCreate,
    DataRead,
    GraphTypeBase,
    GraphTypeRead,
)
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
@app.post("/create_graph_type", response_model=GraphTypeRead)
async def create_graph_type(
    graph_type: GraphTypeBase, session: AsyncSession = Depends(get_async_session)
):
    repo = GraphTypeRepository(session)
    existing = await repo.find_by_name(graph_type.name)
    if existing:
        return existing
    
    new_graph_type = await repo.create(name=graph_type.name, unit=graph_type.unit)
    return new_graph_type


@app.get("/graph_types", response_model=List[GraphTypeRead])
async def graph_types(session: AsyncSession = Depends(get_async_session)):
    repo = GraphTypeRepository(session)
    types = await repo.get_all()
    return types


# Collector Endpoints
@app.post("/create_collector", response_model=CollectorRead)
async def create_collector(
    collector: CollectorCreate, session: AsyncSession = Depends(get_async_session)
):
    repo = CollectorRepository(session)
    existing = await repo.find_by_display_name(collector.display_name)
    if existing:
        return existing
    
    new_collector = await repo.create(display_name=collector.display_name)
    return new_collector


@app.get("/collectors", response_model=List[CollectorRead])
async def collectors(session: AsyncSession = Depends(get_async_session)):
    repo = CollectorRepository(session)
    collectors = await repo.get_all()
    return collectors


@app.get("/collector/{collector_id}", response_model=CollectorRead)
async def collector(collector_id: int, session: AsyncSession = Depends(get_async_session)):
    repo = CollectorRepository(session)
    collector = await repo.get_by_id(collector_id)
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    return collector


# Data Endpoints
@app.post("/create_data", response_model=DataRead)
async def create_data(
    data: DataCreate,
    session: AsyncSession = Depends(get_async_session),
):
    repo = DataRepository(session)
    new_data = await repo.create(
        collector_id=data.collector_id, 
        graph_type_id=data.graph_type_id, 
        content=data.content
    )
    return new_data


@app.get("/data", response_model=List[DataRead])
async def data(
    collector_id: int,
    graph_type_id: int | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    repo = DataRepository(session)
    data_points = await repo.find_by_collector_and_graph_type(collector_id, graph_type_id, limit)
    return data_points
