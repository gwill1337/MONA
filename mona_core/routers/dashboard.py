from datetime import UTC, datetime, timedelta

from fastapi import Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mona_core.db import Anomaly, Metric, TrainedModel
from mona_core.schemas import DashboardAnomaly, DashboardMetric, DashboardOut, ModelInfo
from mona_core.security import (
    get_db,
    user_router,
)


@user_router.get("/dashboard", response_model=DashboardOut)
def get_dashboard_data(
    hours: int = 1,
    start: datetime | None = None,
    end: datetime | None = None,
    device: str | None = None,
    max_points: int = Query(default=2000, le=10000),
    db: Session = Depends(get_db),
) -> DashboardOut:
    devices = list(db.scalars(select(Metric.device).distinct()).all())

    now = datetime.now(UTC)

    since: datetime | None
    until: datetime

    if start and end:
        since = start
        until = end
        delta_hours = (until - since).total_seconds() / 3600
    else:
        delta_hours = hours if hours and hours > 0 else 720
        since = now - timedelta(hours=delta_hours) if hours and hours > 0 else None
        until = now

    if delta_hours >= 168:
        bucket_seconds = 3600
    elif delta_hours > 12:
        bucket_seconds = 600
    else:
        bucket_seconds = 60

    epoch_bucket = (
        func.floor(func.extract("epoch", Metric.timestamp) / bucket_seconds)
        * bucket_seconds
    )
    bucket_timestamp = func.to_timestamp(epoch_bucket)

    stmt_m = (
        select(
            Metric.device,
            bucket_timestamp.label("timestamp"),
            func.avg(Metric.cpu).label("cpu"),
            func.avg(Metric.ram).label("ram"),
        )
        .group_by(Metric.device, epoch_bucket)
        .order_by(epoch_bucket.asc())
        .limit(max_points)
    )

    stmt_a = select(Anomaly).order_by(Anomaly.timestamp.asc())

    if device:
        stmt_m = stmt_m.where(Metric.device == device)
        stmt_a = stmt_a.where(Anomaly.device == device)
    if since:
        stmt_m = stmt_m.where(Metric.timestamp >= since)
        stmt_a = stmt_a.where(Anomaly.timestamp >= since)
    if until:
        stmt_m = stmt_m.where(Metric.timestamp <= until)
        stmt_a = stmt_a.where(Anomaly.timestamp <= until)

    raw_metrics = db.execute(stmt_m).all()

    metrics = [
        DashboardMetric(
            id=i,
            device=row.device,
            cpu=float(row.cpu),
            ram=float(row.ram),
            timestamp=row.timestamp,
        )
        for i, row in enumerate(raw_metrics)
    ]

    anomalies = list(db.scalars(stmt_a).all())

    model_record = db.scalars(
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    ).first()

    return DashboardOut(
        devices=devices,
        model=ModelInfo.model_validate(model_record) if model_record else None,
        metrics=[DashboardMetric.model_validate(m) for m in metrics],
        anomalies=[DashboardAnomaly.model_validate(a) for a in anomalies],
    )
