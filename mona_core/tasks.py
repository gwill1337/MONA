"""Metric collection and user-model training Celery tasks."""

import logging
import math
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import httpx2
import numpy as np
from sqlalchemy import select

from mona_core import model_registry
from mona_core.anomaly_core import (
    dump_model,
    fit_detector,
    known_anomaly_mask,
    to_epoch,
    training_blocks,
)
from mona_core.celery_conf import app
from mona_core.db import Anomaly, Device, Metric, SessionLocal, TrainedModel

logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-main-metrics.mona.svc:9090",
).rstrip("/")

MAX_STORED_MODELS = 10
MIN_TRAINING_POINTS = 30
PROMETHEUS_TIMEOUT_SECONDS = 5.0

CPU_QUERY = (
    "100 * (1 - avg by (job) ("
    'rate(node_cpu_seconds_total{physical_pc="true",mode="idle"}[1m])))'
)
RAM_QUERY = (
    "avg by (job) ((1 - ("
    'node_memory_MemAvailable_bytes{physical_pc="true"} / '
    'node_memory_MemTotal_bytes{physical_pc="true"})) * 100)'
)


def _query_prometheus(client: httpx2.Client, query: str) -> dict[str, float]:
    """Return {job: value} for a grouped query; empty when the query fails."""
    try:
        response = client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
        )
        response.raise_for_status()
        series_list = response.json().get("data", {}).get("result", [])

        values: dict[str, float] = {}
        for series in series_list:
            job = series["metric"].get("job")
            value = float(series["value"][1])
            if job and math.isfinite(value):
                values[job] = value
        return values
    except (httpx2.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Prometheus query failed; storing 0.0 for all devices: %s", exc)
        return {}


def _parse_exporters() -> dict[str, str]:
    """Parse EXPORTERS="name:ip,name:ip" into {name: ip}."""
    exporters: dict[str, str] = {}
    for entry in os.getenv("EXPORTERS", "").split(","):
        name, separator, ip = entry.partition(":")
        name, ip = name.strip(), ip.strip()
        if separator and name and ip:
            exporters[name] = ip
    return exporters


@app.task(name="tasks.collect_and_save")
def collect_and_save():
    """Collect CPU/RAM metrics from configured physical-PC exporters."""
    db = SessionLocal()
    try:
        existing = {device.name: device for device in db.scalars(select(Device)).all()}
        for name, ip in _parse_exporters().items():
            device = existing.get(name)
            if device is None:
                db.add(Device(name=name, ip=ip, is_active=True))
            elif device.ip != ip:
                device.ip = ip
        db.commit()

        active_devices = db.scalars(
            select(Device).where(Device.is_active.is_(True))
        ).all()

        with httpx2.Client(timeout=PROMETHEUS_TIMEOUT_SECONDS) as client:
            cpu_by_job = _query_prometheus(client, CPU_QUERY)
            ram_by_job = _query_prometheus(client, RAM_QUERY)

        results = []
        for device in active_devices:
            cpu = cpu_by_job.get(device.name, 0.0)
            ram = ram_by_job.get(device.name, 0.0)
            db.add(Metric(cpu=cpu, ram=ram, device=device.name))
            results.append(
                {"device": device.name, "cpu": round(cpu, 2), "ram": round(ram, 2)}
            )

        db.commit()
        return results

    except Exception as exc:
        db.rollback()
        logger.exception("Error collecting metrics")
        return {"error": str(exc)}
    finally:
        db.close()


@app.task(name="tasks.train_model_task", soft_time_limit=900, time_limit=960)
def train_model_task(hours: float, note: str = "", activate: bool = True):
    """Train a user Isolation Forest model on the requested historical period."""
    db = SessionLocal()
    try:
        since = datetime.now(UTC) - timedelta(hours=hours)
        rows = db.execute(
            select(Metric.device, Metric.timestamp, Metric.cpu, Metric.ram)
            .where(Metric.timestamp >= since, Metric.device.is_not(None))
            .order_by(Metric.timestamp)
        ).all()

        by_device: dict[str, list] = defaultdict(list)
        for row in rows:
            by_device[row.device].append(row)

        blocks: list[np.ndarray] = []
        period_bounds: list[tuple[datetime, datetime]] = []
        excluded_points = 0

        for device_name, device_rows in by_device.items():
            stamps = [row.timestamp for row in device_rows]
            ts = to_epoch(stamps)
            cpu = np.asarray([row.cpu for row in device_rows], dtype=float)
            ram = np.asarray([row.ram for row in device_rows], dtype=float)

            anomaly_times = db.scalars(
                select(Anomaly.timestamp).where(Anomaly.device == device_name)
            ).all()
            excluded = known_anomaly_mask(ts, cpu, ram, anomaly_times)
            excluded_points += int(excluded.sum())

            features, used = training_blocks(ts, cpu, ram, ~excluded)
            if len(features):
                blocks.append(features)
                period_bounds.append((stamps[used[0]], stamps[used[-1]]))

        n_points = sum(len(block) for block in blocks)
        if n_points < MIN_TRAINING_POINTS:
            return {
                "status": "error",
                "message": (
                    f"Not enough clean data for training (found {n_points} points after "
                    f"excluding {excluded_points} known-anomaly points; "
                    f"minimum {MIN_TRAINING_POINTS} required)"
                ),
            }

        model, scaler = fit_detector(np.vstack(blocks))

        record = TrainedModel(
            model_data=dump_model(model, scaler),
            trained_by=model_registry.USER,
            points_count=n_points,
            period_from=min(start for start, _ in period_bounds),
            period_to=max(end for _, end in period_bounds),
            note=(note or "").strip() or None,
            is_active=False,
        )
        db.add(record)
        db.flush()

        if activate:
            model_registry.activate(db, record.id)

        model_registry.prune(db, keep=MAX_STORED_MODELS)
        db.commit()

        return {
            "status": "success",
            "message": (
                f"Model trained on {n_points} clean points over the last {hours} h "
                f"({len(blocks)} device(s)); excluded {excluded_points} points "
                "around known anomalies."
                + ("" if activate else " Saved, not activated.")
            ),
        }

    except Exception:
        db.rollback()
        logger.exception("Server error during training model")
        return {"status": "error", "message": "Server error"}
    finally:
        db.close()
