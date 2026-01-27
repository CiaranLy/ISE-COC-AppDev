from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import DataIngest, DataIngestResponse
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


@app.post("/aggregator", response_model=DataIngestResponse)
async def aggregate_data(
    data: DataIngest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Ingest data from collectors.
    
    This endpoint:
    1. Creates or finds a collector by name
    2. Creates or finds a graph_type by collector name and unit
    3. Creates a data entry with the provided content and timestamp
    """
    # Step 1: Get or create collector
    collector_repo = CollectorRepository(session)
    collector = await collector_repo.find_by_display_name(data.collector_name)
    
    if not collector:
        collector = await collector_repo.create(display_name=data.collector_name)
    
    # Step 2: Get or create graph_type
    # Using collector_name as the graph type name (you can adjust this logic)
    graph_type_repo = GraphTypeRepository(session)
    graph_type = await graph_type_repo.find_by_name(data.collector_name)
    
    if not graph_type:
        graph_type = await graph_type_repo.create(
            name=data.collector_name,
            unit=data.unit
        )
    
    # Step 3: Create data entry
    data_repo = DataRepository(session)
    
    # Use provided timestamp or default to now
    if data.timestamp:
        new_data = await data_repo.create(
            collector_id=collector.id,
            graph_type_id=graph_type.id,
            content=data.content,
            timestamp_utc=data.timestamp
        )
    else:
        new_data = await data_repo.create(
            collector_id=collector.id,
            graph_type_id=graph_type.id,
            content=data.content
        )
    
    return DataIngestResponse(
        success=True,
        collector_id=collector.id,
        graph_type_id=graph_type.id,
        data_id=new_data.id,
        message="Data ingested successfully"
    )
