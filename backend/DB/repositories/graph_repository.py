"""Graph repository."""

from typing import List, Optional

from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from DB.models.graph import Graph
from DB.repositories.base import AsyncRepository


class GraphRepository(AsyncRepository[Graph]):
    model_cls = Graph

    async def find_by_collector_unit_and_session(
        self, collector_id: int, unit: str, session_id: str
    ) -> Optional[Graph]:
        query = select(Graph).where(
            Graph.collector_id == collector_id,
            Graph.unit == unit,
            Graph.session_id == session_id,
        )
        result = await self.async_session.execute(query)
        return result.scalars().first()

    async def update_max_value(self, graph_id: int, max_value) -> bool:
        query = update(Graph).where(Graph.id == graph_id).values(max_value=max_value)
        result = await self.async_session.execute(query)
        return result.rowcount > 0

    async def get_sessions_with_data(
        self,
        session_offset: int,
        session_limit: int,
        collector_id: Optional[int] = None,
    ) -> List[Graph]:
        """
        Get graphs for a window of sessions, ordered by when the graph was created.

        A "session" here is defined by Graph.session_id. We determine recency by the
        latest Graph.time_created within each session across all graphs.
        If collector_id is provided, only sessions containing that collector are returned.
        """
        session_subquery_base = (
            select(
                Graph.session_id,
                func.max(Graph.time_created).label("last_ts"),
            )
            .group_by(Graph.session_id)
        )

        if collector_id is not None:
            session_subquery_base = session_subquery_base.where(Graph.collector_id == collector_id)

        session_subquery = (
            session_subquery_base
            .order_by(func.max(Graph.time_created).desc())
            .offset(session_offset)
            .limit(session_limit)
            .subquery()
        )

        query = (
            select(Graph)
            .join(session_subquery, Graph.session_id == session_subquery.c.session_id)
            .options(selectinload(Graph.data_points), selectinload(Graph.collector))
            .order_by(session_subquery.c.last_ts.desc(), Graph.collector_id, Graph.unit)
        )

        if collector_id is not None:
            query = query.where(Graph.collector_id == collector_id)

        result = await self.async_session.execute(query)
        return list(result.scalars().all())

    async def get_by_session_id(self, session_id: str) -> List[Graph]:
        """Get all graphs for a specific session_id, newest graphs first."""
        query = (
            select(Graph)
            .where(Graph.session_id == session_id)
            .options(selectinload(Graph.data_points), selectinload(Graph.collector))
            .order_by(Graph.time_created.desc(), Graph.collector_id, Graph.unit)
        )
        result = await self.async_session.execute(query)
        return list(result.scalars().all())
