import os
from datetime import UTC, datetime, timedelta

from celery import Celery
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from mona_core.db import (
    Anomaly,
    Base,
    Device,
    Metric,
    SessionLocal,
    TrainedModel,
    engine,
)

Base.metadata.create_all(engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:30081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
celery_client = Celery("mona", broker=redis_url, backend=redis_url)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ─── helpers ────────────────────────────────────────────────────────────────
class DeviceCreate(BaseModel):
    ip: str
    name: str
    is_active: bool = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── API endpoints ──────────────────────────────────────────────────────────
# ─── Probes (Liveness & Readiness) ──────────────────────────────────────────
@app.get("/health/live", tags=["Health"])
def liveness_probe():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_probe(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


# ─── Devices ────────────────────────────────────────────────────────────────


@app.get("/devices")
def list_devices(db: Session = Depends(get_db)):
    stmt = select(Device)
    return db.execute(stmt).scalars().all()


@app.post("/devices", status_code=201)
def create_device(body: DeviceCreate, db: Session = Depends(get_db)):
    dev = Device(ip=body.ip, name=body.name, is_active=body.is_active)
    db.add(dev)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Name already exists")
    db.refresh(dev)
    return dev


@app.delete("/devices/{device_id}")
def delete_device(device_id, db: Session = Depends(get_db)):
    stmt = delete(Device).where(Device.id == device_id)
    try:
        result = db.execute(stmt)

        if result.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=404, detail="Device not found")

        db.commit()

        return {"message": "Device deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/prometheus/targets")
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


# ─── Model ──────────────────────────────────────────────────────────────────
@app.get("/anomalies")
def get_anomalies(
    hours: int = 24, device: str | None = None, db: Session = Depends(get_db)
):
    stmt = select(Anomaly)
    if device:
        stmt = stmt.where(Anomaly.device == device)
    if hours > 0:
        stmt = stmt.where(
            Anomaly.timestamp >= datetime.now(UTC) - timedelta(hours=hours)
        )

    stmt = stmt.order_by(Anomaly.timestamp.desc())
    anomalies = db.execute(stmt).scalars().all()
    return [
        {
            "id": a.id,
            "metric_id": a.metric_id,
            "cpu": a.cpu,
            "ram": a.ram,
            "timestamp": a.timestamp,
            "reason": a.reason,
            "score": a.score,
            "detected_at": a.detected_at,
            "device": a.device,
        }
        for a in anomalies
    ]


@app.get("/model-info")
def model_info(db: Session = Depends(get_db)):
    stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    )

    record = db.execute(stmt).scalar_one_or_none()

    if record is None:
        return {
            "status": "no_model",
            "message": "Model is not manually trained yet. Using auto-mode.",
        }
    return {
        "status": "ok",
        "model": {
            "trained_at": record.trained_at,
            "trained_by": record.trained_by,
            "points_count": record.points_count,
            "period_from": record.period_from,
            "period_to": record.period_to,
            "note": record.note,
        },
    }


@app.post("/train", status_code=202)
def train_model(
    hours: float = Query(
        default=1.0, description="Hours of recent data to use for training"
    ),
    note: str = Query(default="", description="Comment (optional)"),
):

    task = celery_client.send_task(
        "tasks.train_model_task", kwargs={"hours": hours, "note": note}
    )

    return {
        "status": "accepted",
        "message": "Model training task has been submitted to the background.",
        "task_id": task.id,
    }


@app.delete("/model")
def delete_model(db: Session = Depends(get_db)):
    """Deletes the custom model — Celery will return to auto-mode."""
    try:
        stmt = delete(TrainedModel).where(TrainedModel.trained_by == "user")
        result = db.execute(stmt)
        db.commit()
        return {
            "status": "ok",
            "deleted": result.rowcount,  # type: ignore
            "message": "Model deleted. Celery switched to auto-mode.",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")


# ─── Dashboard ──────────────────────────────────────────────────────────────
@app.get("/api/dashboard")
def get_dashboard_data(
    hours: int = 1, device: str | None = None, db: Session = Depends(get_db)
):
    devices_stmt = select(Metric.device).distinct()
    devices = db.execute(devices_stmt).scalars().all()

    since = datetime.now(UTC) - timedelta(hours=hours) if hours > 0 else None

    stmt_m = select(Metric)
    stmt_a = select(Anomaly)

    if device:
        stmt_m = stmt_m.where(Metric.device == device)
        stmt_a = stmt_a.where(Anomaly.device == device)
    if since:
        stmt_m = stmt_m.where(Metric.timestamp >= since)
        stmt_a = stmt_a.where(Anomaly.timestamp >= since)

    metrics = db.execute(stmt_m.order_by(Metric.timestamp)).scalars().all()
    anomalies = db.execute(stmt_a.order_by(Anomaly.timestamp)).scalars().all()

    model_stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    )
    model_record = db.execute(model_stmt).scalar_one_or_none()

    model_info = None
    if model_record:
        model_info = {
            "trained_at": model_record.trained_at.isoformat(),
            "points_count": model_record.points_count,
            "period_from": model_record.period_from.isoformat()
            if model_record.period_from
            else None,
            "period_to": model_record.period_to.isoformat()
            if model_record.period_to
            else None,
            "note": model_record.note,
        }

    return {
        "devices": devices,
        "model": model_info,
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu": m.cpu,
                "ram": m.ram,
                "device": m.device,
            }
            for m in metrics
        ],
        "anomalies": [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "cpu": a.cpu,
                "ram": a.ram,
                "reason": a.reason,
                "score": a.score,
                "device": a.device,
            }
            for a in anomalies
        ],
    }


# ─── Metrics ────────────────────────────────────────────────────────────────
@app.get("/db-metrics")
def get_metrics(device: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Metric)
    if device:
        stmt = stmt.where(Metric.device == device)
    return db.execute(stmt).scalars().all()


# ─── Tasks ──────────────────────────────────────────────────────────────────
@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    result = celery_client.AsyncResult(task_id)

    raw = None
    if result.ready():
        try:
            raw = result.result
            if isinstance(raw, Exception):
                raw = {"error": str(raw)}
        except Exception:
            raw = None

    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.ready() else None,
    }
