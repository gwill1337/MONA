from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from prometheus_client.core import REGISTRY, GaugeMetricFamily
from sqlalchemy import select
from sqlalchemy.orm import Session

from mona_core.db import Anomaly, Device, Metric, SessionLocal
from mona_core.schemas import MetricSchema, MetricsOut
from mona_core.security import (
    get_db,
    user_router,
)

router_prometheus = APIRouter()


class AnomalyCollector(object):
    def collect(self):
        gauge = GaugeMetricFamily(
            "mona_anomaly_active",
            "Active ML anomalies detected in the last 3 minutes",
            labels=["device", "reason"],
        )

        db = SessionLocal()
        try:
            cutoff = datetime.now(UTC) - timedelta(minutes=0.2)

            query = select(Anomaly).where(
                Anomaly.timestamp >= cutoff.replace(tzinfo=None)
            )
            recent_anomalies = db.execute(query).scalars().all()

            seen = set()
            for a in recent_anomalies:
                label_values = (a.device, a.reason)
                if label_values not in seen:
                    gauge.add_metric([a.device, a.reason], 1)
                    seen.add(label_values)
        except Exception as e:
            print(f"Error in Prometheus AnomalyCollector: {e}")
        finally:
            db.close()

        yield gauge


try:
    REGISTRY.register(AnomalyCollector())
except ValueError:
    pass


@router_prometheus.get("/api/prometheus/targets", tags=["Prometheus"])
def get_prometheus_targets(db: Session = Depends(get_db)):
    stmt = select(Device).where(Device.is_active, Device.ip.is_not(None))
    devices = db.execute(stmt).scalars().all()

    targets = []
    for dev in devices:
        targets.append(
            {
                "targets": [f"{dev.ip}:9100"],
                "labels": {
                    "job": dev.name,
                    "physical_pc": "true",
                    "device_label": dev.name,
                },
            }
        )
    return targets


@user_router.get("/db-metrics", response_model=MetricsOut)
def get_metrics(
    device: str | None = None,
    hours: int = Query(default=1, le=24 * 7),
    before: datetime | None = None,
    limit: int = Query(default=500, le=5000),
    db: Session = Depends(get_db),
) -> MetricsOut:
    since = datetime.now(UTC) - timedelta(hours=hours)
    stmt = select(Metric).where(Metric.timestamp >= since)
    if device:
        stmt = stmt.where(Metric.device == device)
    if before:
        stmt = stmt.where(Metric.timestamp < before)
    stmt = stmt.order_by(Metric.timestamp.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    next_cursor = rows[-1].timestamp if len(rows) == limit else None
    return MetricsOut(
        items=[MetricSchema.model_validate(m) for m in rows], next_cursor=next_cursor
    )
