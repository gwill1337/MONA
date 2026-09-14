import logging
import os
from datetime import UTC, datetime, timedelta

# import requests
import httpx2
import skops.io as sio
from sqlalchemy import select

from mona_core.celery_conf import app
from mona_core.config import settings
from mona_core.db import Device, Metric, SessionLocal, TrainedModel

# ─── Logger ─────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─── Helpers ────────────────────────────────────────────────────────────────

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-main-metrics.mona.svc:9090",
)


# def _query(prometheus_url: str, query: str) -> float:
#     resp = requests.get(
#         f"{prometheus_url}/api/v1/query",
#         params={"query": query},
#         timeout=5,
#     )
#     data = resp.json()
#     return float(data["data"]["result"][0]["value"][1]) if data["data"]["result"] else 0


def _query(prometheus_url: str, query: str) -> float:
    # Использование httpx.Client или разового запроса httpx.get()
    try:
        resp = httpx2.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return (
            float(data["data"]["result"][0]["value"][1])
            if data["data"]["result"]
            else 0.0
        )
    except (httpx2.HTTPError, KeyError, IndexError) as e:
        logger.warning(f"Failed to query Prometheus: {e}")
        return 0.0


def _build_features(rows):
    import numpy as np

    if len(rows) < 5:
        raise ValueError("Need at least 5 points")

    cpu = np.array([r.cpu for r in rows], dtype=float)
    ram = np.array([r.ram for r in rows], dtype=float)
    cpu_d1 = np.concatenate([[0], np.diff(cpu)])
    ram_d1 = np.concatenate([[0], np.diff(ram)])
    cpu_d5 = np.concatenate([[0] * 5, cpu[5:] - cpu[:-5]])
    ram_d5 = np.concatenate([[0] * 5, ram[5:] - ram[:-5]])
    return np.column_stack([cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5])


# ─── Tasks ──────────────────────────────────────────────────────────────────


# @app.task(name="tasks.collect_and_save")
# def collect_and_save():
#     """CPU/RAM metrics from physical PCs via custom Prometheus."""
#     db = SessionLocal()
#     try:
#         config_devices = os.getenv("EXPORTERS", "").split(",")

#         for entry in config_devices:
#             if not entry or ":" not in entry:
#                 continue

#             device_name, device_ip = entry.split(":", 1)
#             existing = db.execute(
#                 select(Device).where(Device.name == device_name)
#             ).scalar_one_or_none()
#             if not existing:
#                 new_dev = Device(name=device_name, ip=device_ip, is_active=True)
#                 db.add(new_dev)
#             elif existing.ip != device_ip:
#                 existing.ip = device_ip

#         db.commit()

#         active_devices = (
#             db.execute(select(Device).where(Device.is_active)).scalars().all()
#         )

#         results = []
#         for dev in active_devices:
#             job = dev.name
#             sel = f'job="{job}",physical_pc="true"'
#             cpu_query = f'100 * (1 - avg(rate(node_cpu_seconds_total{{{sel},mode="idle"}}[5m])))'
#             ram_query = (
#                 f"avg((1 - (node_memory_MemAvailable_bytes{{{sel}}}"
#                 f" / node_memory_MemTotal_bytes{{{sel}}})) * 100)"
#             )
#             cpu = _query(PROMETHEUS_URL, cpu_query)
#             ram = _query(PROMETHEUS_URL, ram_query)

#             metric = Metric(cpu=cpu, ram=ram, device=job)
#             db.add(metric)
#             results.append({"device": job, "cpu": round(cpu, 2), "ram": round(ram, 2)})

#         db.commit()
#         return results
#     except Exception as e:
#         db.rollback()
#         logger.exception("Error collecting metrics")
#         return {"error": str(e)}
#     finally:
#         db.close()


@app.task(name="tasks.collect_and_save")
def collect_and_save():
    """CPU/RAM metrics from physical PCs via custom Prometheus."""
    db = SessionLocal()
    try:
        config_devices = os.getenv("EXPORTERS", "").split(",")

        for entry in config_devices:
            if not entry or ":" not in entry:
                continue

            device_name, device_ip = entry.split(":", 1)
            existing = db.execute(
                select(Device).where(Device.name == device_name)
            ).scalar_one_or_none()
            if not existing:
                new_dev = Device(name=device_name, ip=device_ip, is_active=True)
                db.add(new_dev)
            elif existing.ip != device_ip:
                existing.ip = device_ip

        db.commit()

        active_devices = (
            db.execute(select(Device).where(Device.is_active)).scalars().all()
        )

        results = []
        with httpx2.Client(base_url=PROMETHEUS_URL, timeout=0.5) as client:
            for dev in active_devices:
                job = dev.name
                sel = f'job="{job}",physical_pc="true"'
                cpu_query = f'100 * (1 - avg(rate(node_cpu_seconds_total{{{sel},mode="idle"}}[5m])))'
                ram_query = (
                    f"avg((1 - (node_memory_MemAvailable_bytes{{{sel}}}"
                    f" / node_memory_MemTotal_bytes{{{sel}}})) * 100)"
                )
                try:
                    cpu_resp = client.get(
                        "/api/v1/query", params={"query": cpu_query}
                    ).json()
                    ram_resp = client.get(
                        "/api/v1/query", params={"query": ram_query}
                    ).json()

                    cpu = (
                        float(cpu_resp["data"]["result"][0]["value"][1])
                        if cpu_resp.get("data", {}).get("result")
                        else 0.0
                    )
                    ram = (
                        float(ram_resp["data"]["result"][0]["value"][1])
                        if ram_resp.get("data", {}).get("result")
                        else 0.0
                    )
                except (httpx2.HTTPError, KeyError, IndexError) as err:
                    logger.warning(
                        f"Failed to fetch Prometheus metrics for {job}: {err}"
                    )
                    cpu, ram = 0.0, 0.0

                metric = Metric(cpu=cpu, ram=ram, device=job)
                db.add(metric)
                results.append(
                    {"device": job, "cpu": round(cpu, 2), "ram": round(ram, 2)}
                )

            db.commit()
            return results
    except Exception as e:
        db.rollback()
        logger.exception("Error collecting metrics")
        return {"error": str(e)}
    finally:
        db.close()


@app.task(name="tasks.train_model_task")
def train_model_task(hours: float, note: str):
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    db = SessionLocal()
    try:
        since = datetime.now(UTC) - timedelta(hours=hours)
        rows = (
            db.execute(
                select(Metric)
                .where(Metric.cpu > 0.1)
                .where(Metric.timestamp >= since)
                .order_by(Metric.timestamp)
            )
            .scalars()
            .all()
        )

        if len(rows) < 30:
            return {
                "status": "error",
                "message": f"Not enough data for training (found {len(rows)}, minimum 30 required)",
            }

        X_raw = _build_features(rows)  # noqa: N806
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)  # noqa: N806

        model = IsolationForest(
            n_estimators=200,
            contamination=settings.contamination,
            random_state=42,
        )
        model.fit(X_scaled)

        model_bytes = sio.dumps((model, scaler))

        record = TrainedModel(
            model_data=model_bytes,
            trained_by="user",
            points_count=len(rows),
            period_from=rows[0].timestamp,
            period_to=rows[-1].timestamp,
            note=note.strip() or None,
        )
        db.add(record)
        db.commit()

        return {
            "status": "success",
            "message": f"Model trained on {len(rows)} points over the last {hours} h.",
        }

    except Exception:
        db.rollback()
        logger.exception("Server error during training model")
        return {"status": "error", "message": "Server error"}
    finally:
        db.close()
