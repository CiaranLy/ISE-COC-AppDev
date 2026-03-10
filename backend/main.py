from collections import deque
from contextlib import asynccontextmanager
from typing import List

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import AlertCreate, AlertResponse, DataIngest, DataIngestResponse, ErrorResponse, GraphWithDataResponse, SimpleDataPoint, ThresholdUpdate
from config import API_TITLE, API_VERSION, CORS_ORIGINS, UVICORN_HOST, UVICORN_PORT, UVICORN_WORKERS
from DB.database import get_async_session, init_db
from DB.repositories import AlertRepository, CollectorRepository, DataRepository, GraphRepository
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
recent_data_cache = deque(maxlen=50)

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
    return {"message": "Data Collector API", "recent_data": list(recent_data_cache)}


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

    recent_data_cache.appendleft({
        "collector_name": data.collector_name,
        "content": data.content,
        "unit": data.unit,
        "session_id": data.session_id,
        "timestamp": data.timestamp.isoformat(),
        "message_id": data.message_id
    })


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
async def get_all_graphs(
    session: AsyncSession = Depends(get_async_session),
    session_offset: int = Query(0, ge=0),
    session_limit: int = Query(3, ge=1, le=100),
):
    """
    Get graphs for a window of sessions with their data points.

    Sessions are ordered by most recent data point (newest session first).
    Each graph is unique by (collector, unit, session_id).
    """
    graph_repo = GraphRepository(session)
    graphs = await graph_repo.get_sessions_with_data(
        session_offset=session_offset,
        session_limit=session_limit,
    )

    if not graphs:
        # Use 404 to indicate that we've paged past the available sessions
        raise HTTPException(status_code=404, detail="No graphs available for this page.")

    return [
        GraphWithDataResponse(
            id=graph.id,
            collector_id=graph.collector_id,
            collector_name=graph.collector.display_name,
            unit=graph.unit,
            session_id=graph.session_id,
            max_value=graph.max_value,
            data_points=[
                SimpleDataPoint(
                    timestamp=point.timestamp_utc.timestamp(),
                    value=point.content
                )
                for point in sorted(graph.data_points, key=lambda p: p.timestamp_utc)
            ],
        )
        for graph in graphs
    ]


@v1.put("/graphs/{graph_id}/threshold", response_model=None, status_code=204)
async def set_graph_threshold(
    graph_id: int,
    body: ThresholdUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Set or clear the max_value threshold for a graph."""
    graph_repo = GraphRepository(session)
    await graph_repo.update_max_value(graph_id, body.max_value)
    logger.info("Updated threshold for graph %d: %s", graph_id, body.max_value)


@v1.post("/alerts", response_model=AlertResponse, status_code=201)
async def create_alert(
    body: AlertCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create an alert when a value exceeds its threshold."""
    alert_repo = AlertRepository(session)
    alert = await alert_repo.create(
        collector_name=body.collector_name,
        unit=body.unit,
        value=body.value,
        threshold=body.threshold,
    )
    logger.info(
        "Alert created: collector=%s unit=%s value=%s threshold=%s",
        body.collector_name, body.unit, body.value, body.threshold,
    )
    return AlertResponse(
        id=alert.id,
        collector_name=alert.collector_name,
        unit=alert.unit,
        value=alert.value,
        threshold=alert.threshold,
    )


@v1.get("/alerts/pending", response_model=list[AlertResponse])
async def get_pending_alerts(
    collector_name: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Get unacknowledged alerts for a collector."""
    alert_repo = AlertRepository(session)
    alerts = await alert_repo.get_pending(collector_name)
    return [
        AlertResponse(
            id=a.id,
            collector_name=a.collector_name,
            unit=a.unit,
            value=a.value,
            threshold=a.threshold,
        )
        for a in alerts
    ]


@v1.post("/alerts/{alert_id}/acknowledge", response_model=None, status_code=204)
async def acknowledge_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Mark an alert as acknowledged."""
    alert_repo = AlertRepository(session)
    await alert_repo.acknowledge(alert_id)


app.include_router(v1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=UVICORN_HOST,
        port=UVICORN_PORT,
        workers=UVICORN_WORKERS,
    )
