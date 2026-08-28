from datetime import UTC, datetime, timedelta

from fastapi import Depends, Query
from sqlalchemy import select
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
    device: str | None = None,
    max_points: int = Query(default=2000, le=10000),
    db: Session = Depends(get_db),
) -> DashboardOut:

    devices = list(db.scalars(select(Metric.device).distinct()).all())

    since = datetime.now(UTC) - timedelta(hours=hours) if hours > 0 else None

    stmt_m = select(Metric)
    stmt_a = select(Anomaly)

    if device:
        stmt_m = stmt_m.where(Metric.device == device)
        stmt_a = stmt_a.where(Anomaly.device == device)
    if since:
        stmt_m = stmt_m.where(Metric.timestamp >= since)
        stmt_a = stmt_a.where(Anomaly.timestamp >= since)

    stmt_m = stmt_m.order_by(Metric.timestamp.desc()).limit(max_points)
    stmt_a = stmt_a.order_by(Anomaly.timestamp.desc()).limit(max_points)

    metrics = list(reversed(db.scalars(stmt_m).all()))
    anomalies = list(reversed(db.scalars(stmt_a).all()))

    model_stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    )
    model_record = db.scalars(model_stmt).first()

    return DashboardOut(
        devices=devices,
        model=ModelInfo.model_validate(model_record) if model_record else None,
        metrics=[DashboardMetric.model_validate(m) for m in metrics],
        anomalies=[DashboardAnomaly.model_validate(a) for a in anomalies],
    )
