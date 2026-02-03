"""System metric collectors."""

from datetime import datetime, timezone
from typing import List

import psutil

from data_point import DataPoint


def collect_cpu_percent(collector_name: str) -> DataPoint:
    """Collect CPU usage percentage."""
    cpu_percent = psutil.cpu_percent(interval=None)
    return DataPoint(
        collector_name=collector_name,
        content=cpu_percent,
        unit="cpu_percent",
        timestamp=datetime.now(timezone.utc)
    )


def collect_memory_percent(collector_name: str) -> DataPoint:
    """Collect memory usage percentage."""
    memory = psutil.virtual_memory()
    return DataPoint(
        collector_name=collector_name,
        content=memory.percent,
        unit="memory_percent",
        timestamp=datetime.now(timezone.utc)
    )


def collect_memory_used_mb(collector_name: str) -> DataPoint:
    """Collect memory used in MB."""
    memory = psutil.virtual_memory()
    used_mb = memory.used / (1024 * 1024)
    return DataPoint(
        collector_name=collector_name,
        content=round(used_mb, 2),
        unit="memory_mb",
        timestamp=datetime.now(timezone.utc)
    )


def collect_disk_percent(collector_name: str) -> DataPoint:
    """Collect disk usage percentage for root partition."""
    disk = psutil.disk_usage("/")
    return DataPoint(
        collector_name=collector_name,
        content=disk.percent,
        unit="disk_percent",
        timestamp=datetime.now(timezone.utc)
    )


def collect_all_metrics(collector_name: str) -> List[DataPoint]:
    """Collect all available system metrics."""
    return [
        collect_cpu_percent(collector_name),
        collect_memory_percent(collector_name),
        collect_memory_used_mb(collector_name),
        collect_disk_percent(collector_name),
    ]
