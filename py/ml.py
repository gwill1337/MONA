"""
ml.py — anomaly detection via Isolation Forest.

Two modes:
  1. Trained model exists in DB (trained_by="user") → use it.
     The model knows what the "norm" is — higher accuracy.
  2. No model → train on the fly on the last WINDOW points (fallback).

Features (6 items):
  cpu, ram                — absolute values
  cpu_d1, ram_d1          — change from the previous point
  cpu_d5, ram_d5          — change over 5 points (~25 sec)
"""

import pickle
from datetime import UTC, datetime, timedelta

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from py.celery_conf import app
from py.db import Anomaly, Metric, SessionLocal, TrainedModel

WINDOW = 500
MIN_POINTS = 30
CONTAMINATION = 0.05


# -------- helpers --------


def _build_features(rows):
    """
    Builds a feature matrix with deltas.
    Returns an np.array of shape (N, 6).
    """
    cpu = np.array([r.cpu for r in rows], dtype=float)
    ram = np.array([r.ram for r in rows], dtype=float)

    # Delta from the previous point (i-1)
    cpu_d1 = np.concatenate([[0], np.diff(cpu)])
    ram_d1 = np.concatenate([[0], np.diff(ram)])

    # Delta from 5 points ago
    cpu_d5 = np.concatenate([[0] * 5, cpu[5:] - cpu[:-5]])
    ram_d5 = np.concatenate([[0] * 5, ram[5:] - ram[:-5]])

    return np.column_stack([cpu, ram, cpu_d1, ram_d1, cpu_d5, ram_d5])


def _describe_reason(row, cpu_d1, ram_d1, cpu_d5, ram_d5):
    """Human-readable description of why the point is anomalous."""
    parts = []

    if row.cpu > 85:
        parts.append(f"высокий cpu={row.cpu:.1f}%")
    if row.ram > 85:
        parts.append(f"высокий ram={row.ram:.1f}%")

    if abs(cpu_d1) > 20:
        sign = "▲" if cpu_d1 > 0 else "▼"
        parts.append(f"резкий скачок cpu {sign}{abs(cpu_d1):.1f}%")
    if abs(ram_d1) > 15:
        sign = "▲" if ram_d1 > 0 else "▼"
        parts.append(f"резкий скачок ram {sign}{abs(ram_d1):.1f}%")

    if abs(cpu_d5) > 30:
        parts.append(f"cpu вырос на {cpu_d5:.1f}% за 25 сек")
    if abs(ram_d5) > 20:
        parts.append(f"ram вырос на {ram_d5:.1f}% за 25 сек")

    if not parts:
        parts.append(
            f"комбинированная аномалия (cpu={row.cpu:.1f}%, ram={row.ram:.1f}%)"
        )

    return ", ".join(parts)


def _load_user_model(db):
    """Loads the latest model trained by the user. None if it doesn't exist."""
    record = (
        db.query(TrainedModel)
        .filter(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .first()
    )
    if record is None:
        return None, None
    model, scaler = pickle.loads(record.model_data)
    return model, scaler


# -------- celery task --------


@app.task
def detect_anomalies():
    """Detects anomalies in the last WINDOW metric points."""
    db = SessionLocal()
    try:
        cutoff_new = datetime.now(UTC) - timedelta(minutes=2)

        rows = (
            db.query(Metric)
            .filter(Metric.cpu > 0.1)
            .order_by(Metric.timestamp.desc())
            .limit(WINDOW)
            .all()
        )

        if len(rows) < MIN_POINTS:
            return {
                "status": "skipped",
                "reason": f"мало данных ({len(rows)} точек, нужно {MIN_POINTS}+)",
            }

        rows = list(reversed(rows))

        user_model, user_scaler = _load_user_model(db)

        if user_model is not None:
            # ── Mode 1: custom user model ──
            X_all = _build_features(rows)  # noqa: N806
            X_scaled = user_scaler.transform(X_all)  # noqa: N806
            preds = user_model.predict(X_scaled)
            scores = user_model.decision_function(X_scaled)
            mode = "user_model"
        else:
            # ── Mode 2: on-the-fly training (fallback) ──
            X_all = _build_features(rows)  # noqa: N806
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_all)  # noqa: N806
            model = IsolationForest(
                n_estimators=200,
                contamination=CONTAMINATION,
                random_state=42,
            )
            preds = model.fit_predict(X_scaled)
            scores = model.decision_function(X_scaled)
            mode = "auto"

        existing_ids = {a.metric_id for a in db.query(Anomaly.metric_id).all()}

        new_anomalies = []
        for i, row in enumerate(rows):
            if mode == "auto" and row.timestamp < cutoff_new.replace(tzinfo=None):
                continue
            if preds[i] != -1 or row.id in existing_ids:
                continue

            X_raw = _build_features(rows)  # noqa: N806

            reason = _describe_reason(
                row,
                cpu_d1=X_raw[i, 2],
                ram_d1=X_raw[i, 3],
                cpu_d5=X_raw[i, 4],
                ram_d5=X_raw[i, 5],
            )

            new_anomalies.append(
                Anomaly(
                    metric_id=row.id,
                    cpu=row.cpu,
                    ram=row.ram,
                    timestamp=row.timestamp,
                    reason=reason,
                    score=round(float(scores[i]), 4),
                )
            )

        if new_anomalies:
            db.bulk_save_objects(new_anomalies)
            db.commit()

        return {
            "status": "ok",
            "mode": mode,
            "window": len(rows),
            "anomalies_found": len(new_anomalies),
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
