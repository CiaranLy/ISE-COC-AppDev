from contextlib import asynccontextmanager
from typing import List

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import DataIngest, DataIngestResponse, ErrorResponse, GraphWithDataResponse
from config import API_TITLE, API_VERSION, CORS_ORIGINS, UVICORN_HOST, UVICORN_PORT, UVICORN_WORKERS
from DB.database import get_async_session, init_db
from DB.repositories import CollectorRepository, DataRepository, GraphRepository
from log_config import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", API_TITLE, API_VERSION)
    await init_db()
    logger.info("Application ready")
    yield
    logger.info("Application shutting down")


app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal Server Error", detail=str(exc)).model_dump(),
    )


v1 = APIRouter(prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Data Collector API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@v1.post("/aggregator", response_model=DataIngestResponse)
async def aggregate_data(
    data: DataIngest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Ingest data from collectors.
    
    This endpoint:
    1. Creates or finds a collector by name
    2. Creates or finds a graph by collector_id and unit
    3. Creates a data entry with the provided content and timestamp
    """
    collector_repo = CollectorRepository(session)
    collector = await collector_repo.find_by_display_name(data.collector_name)

    if not collector:
        collector = await collector_repo.create(display_name=data.collector_name)

    graph_repo = GraphRepository(session)
    graph = await graph_repo.find_by_collector_unit_and_session(collector.id, data.unit, data.session_id)

    if not graph:
        graph = await graph_repo.create(
            collector_id=collector.id,
            unit=data.unit,
            session_id=data.session_id,
        )

    data_repo = DataRepository(session)

    new_data = await data_repo.create(
        collector_id=collector.id,
        graph_id=graph.id,
        content=data.content,
        timestamp_utc=data.timestamp,
        session_id=data.session_id,
    )

    logger.info(
        "Ingested data: collector=%s graph=%d value=%s unit=%s",
        data.collector_name, graph.id, data.content, data.unit,
    )

    return DataIngestResponse(
        success=True,
        collector_id=collector.id,
        graph_id=graph.id,
        data_id=new_data.id,
        session_id=data.session_id,
        message="Data ingested successfully",
        message_id=data.message_id,
        acknowledged=True
    )


@v1.get("/graphs", response_model=List[GraphWithDataResponse])
async def get_all_graphs(session: AsyncSession = Depends(get_async_session)):
    """
    Get all graphs with their data points.

    Each graph is unique by (collector, unit, session_id).
    """
    graph_repo = GraphRepository(session)
    graphs = await graph_repo.get_all_with_data()

    return [
        GraphWithDataResponse(
            id=graph.id,
            collector_id=graph.collector_id,
            collector_name=graph.collector.display_name,
            unit=graph.unit,
            session_id=graph.session_id,
            data_points=graph.data_points,
        )
        for graph in graphs
    ]


app.include_router(v1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=UVICORN_HOST,
        port=UVICORN_PORT,
        workers=UVICORN_WORKERS,
    )
