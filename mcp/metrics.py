import json
from datetime import datetime

from server import mcp
from sqlalchemy import func, select

from mona_core.db import Anomaly, Metric, SessionLocal


@mcp.tool()
def get_device_metrics(
    device: str,
    limit: int = 50,
    offset: int = 0,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Get paginated device metrics with optional time filters.

    Args:
        device: Device identifier stored in Metric.device.
        limit: Maximum number of records to return (1-200).
        offset: Number of records to skip.
        start_time: Optional ISO 8601 start timestamp, inclusive.
        end_time: Optional ISO 8601 end timestamp, inclusive.
    """
    if not 1 <= limit <= 200:
        return json.dumps({"error": "limit must be between 1 and 200"})

    if offset < 0:
        return json.dumps({"error": "offset must be >= 0"})

    try:
        start = (
            datetime.fromisoformat(start_time)
            if start_time is not None
            else None
        )
        end = (
            datetime.fromisoformat(end_time)
            if end_time is not None
            else None
        )
    except ValueError:
        return json.dumps({"error": "Invalid ISO 8601 timestamp"})

    if start is not None and end is not None and start > end:
        return json.dumps({"error": "start_time must be <= end_time"})

    filters = [Metric.device == device]

    if start is not None:
        filters.append(Metric.timestamp >= start)

    if end is not None:
        filters.append(Metric.timestamp <= end)

    with SessionLocal() as session:
        total = session.scalar(
            select(func.count()).select_from(Metric).where(*filters)
        )

        metrics = session.scalars(
            select(Metric)
            .where(*filters)
            .order_by(Metric.timestamp.desc(), Metric.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()

        return json.dumps(
            {
                "device": device,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total or 0,
                    "has_more": offset + len(metrics) < (total or 0),
                },
                "data": [
                    {
                        "id": m.id,
                        "device": m.device,
                        "cpu": m.cpu,
                        "ram": m.ram,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in metrics
                ],
            },
            ensure_ascii=False,
        )

@mcp.tool()
def get_mona_anomalies(
    device: str | None = None,
    limit: int = 50,
    offset: int = 0,
    start_time: str | None = None,
    end_time: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
) -> str:
    """Get paginated ML anomalies with optional filters.

    Args:
        device: Optional device identifier.
        limit: Maximum number of anomalies to return (1-200).
        offset: Number of records to skip.
        start_time: Optional ISO 8601 start timestamp, inclusive.
        end_time: Optional ISO 8601 end timestamp, inclusive.
        min_score: Optional minimum anomaly score, inclusive.
        max_score: Optional maximum anomaly score, inclusive.
    """
    if not 1 <= limit <= 200:
        return json.dumps({"error": "limit must be between 1 and 200"})

    if offset < 0:
        return json.dumps({"error": "offset must be >= 0"})

    try:
        start = (
            datetime.fromisoformat(start_time)
            if start_time is not None
            else None
        )
        end = (
            datetime.fromisoformat(end_time)
            if end_time is not None
            else None
        )
    except ValueError:
        return json.dumps({"error": "Invalid ISO 8601 timestamp"})

    if start is not None and end is not None and start > end:
        return json.dumps({"error": "start_time must be <= end_time"})

    if min_score is not None and max_score is not None:
        if min_score > max_score:
            return json.dumps(
                {"error": "min_score must be <= max_score"}
            )

    filters = []

    if device is not None:
        filters.append(Anomaly.device == device)

    if start is not None:
        filters.append(Anomaly.timestamp >= start)

    if end is not None:
        filters.append(Anomaly.timestamp <= end)

    if min_score is not None:
        filters.append(Anomaly.score >= min_score)

    if max_score is not None:
        filters.append(Anomaly.score <= max_score)

    with SessionLocal() as session:
        total = session.scalar(
            select(func.count())
            .select_from(Anomaly)
            .where(*filters)
        )

        anomalies = session.scalars(
            select(Anomaly)
            .where(*filters)
            .order_by(
                Anomaly.detected_at.desc(),
                Anomaly.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        ).all()

        return json.dumps(
            {
                "filters": {
                    "device": device,
                    "start_time": start_time,
                    "end_time": end_time,
                    "min_score": min_score,
                    "max_score": max_score,
                },
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total or 0,
                    "has_more": offset + len(anomalies) < (total or 0),
                },
                "data": [
                    {
                        "id": a.id,
                        "metric_id": a.metric_id,
                        "device": a.device,
                        "cpu": a.cpu,
                        "ram": a.ram,
                        "timestamp": a.timestamp.isoformat(),
                        "detected_at": a.detected_at.isoformat(),
                        "reason": a.reason,
                        "score": a.score,
                    }
                    for a in anomalies
                ],
            },
            ensure_ascii=False,
        )
