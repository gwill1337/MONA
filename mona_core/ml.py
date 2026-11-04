import logging
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mona_core.anomaly_core import (
    ANOMALY_EXCLUSION_AFTER_MINUTES,
    MAX_TRAINING_GAP_SECONDS,
    build_features_segmented,
    fit_detector,
    known_anomaly_mask,
    load_active_model,
    offline_mask,
    to_epoch,
    training_blocks,
)
from mona_core.celery_conf import app
from mona_core.config import settings
from mona_core.db import Anomaly, Metric, SessionLocal

logger = logging.getLogger(__name__)

DETECTION_LOOKBACK_MINUTES = 5
WEAK_COMBINED_LIMIT = 80
ANOMALY_HISTORY_MARGIN = timedelta(
    minutes=ANOMALY_EXCLUSION_AFTER_MINUTES,
    seconds=MAX_TRAINING_GAP_SECONDS,
)


def _describe_reason(
    cpu: float,
    ram: float,
    cpu_d1: float,
    ram_d1: float,
    cpu_d5: float,
    ram_d5: float,
) -> str | None:
    """Explain a detected anomaly; None when no single factor stands out."""
    parts: list[str] = []

    if cpu > 85:
        parts.append(f"high cpu={cpu:.1f}%")
    if ram > 85:
        parts.append(f"high ram={ram:.1f}%")

    if abs(cpu_d1) > 20:
        sign = "▲" if cpu_d1 > 0 else "▼"
        parts.append(f"sudden cpu change {sign}{abs(cpu_d1):.1f}%")
    if abs(ram_d1) > 15:
        sign = "▲" if ram_d1 > 0 else "▼"
        parts.append(f"sudden ram change {sign}{abs(ram_d1):.1f}%")

    if abs(cpu_d5) > 30:
        parts.append(f"cpu changed by {cpu_d5:+.1f}% over 5 samples")
    if abs(ram_d5) > 20:
        parts.append(f"ram changed by {ram_d5:+.1f}% over 5 samples")

    return ", ".join(parts) or None


def _load_user_model(db: Session):
    """Load the active user model, falling back to auto-mode if it cannot be read."""
    try:
        return load_active_model(db)
    except Exception:
        logger.exception("Cannot load the active user model; using auto-mode")
        return None, None


@app.task(name="ml.detect_anomalies")
def detect_anomalies():
    db = SessionLocal()
    try:
        cutoff_new = (
            datetime.now(UTC) - timedelta(minutes=DETECTION_LOOKBACK_MINUTES)
        ).timestamp()

        user_model, user_scaler = _load_user_model(db)
        user_detector = (
            None
            if user_model is None or user_scaler is None
            else (user_model, user_scaler)
        )
        mode = "auto" if user_detector is None else "user_model"

        devices = [
            device
            for device in db.scalars(select(Metric.device).distinct()).all()
            if device
        ]

        new_anomalies: list[dict] = []
        devices_checked = 0

        for device in devices:
            rows_desc = db.scalars(
                select(Metric)
                .where(Metric.device == device)
                .order_by(Metric.timestamp.desc())
                .limit(settings.window)
            ).all()

            if len(rows_desc) < settings.min_points:
                logger.debug(
                    "%s: not enough metric points (%d/%d)",
                    device,
                    len(rows_desc),
                    settings.min_points,
                )
                continue

            rows = list(reversed(rows_desc))
            ts = to_epoch(row.timestamp for row in rows)
            cpu = np.asarray([row.cpu for row in rows], dtype=float)
            ram = np.asarray([row.ram for row in rows], dtype=float)
            features = build_features_segmented(ts, cpu, ram)
            offline = offline_mask(cpu, ram)

            recent_mask = ts >= cutoff_new
            recent_indices = np.flatnonzero(recent_mask).tolist()
            if not recent_indices:
                continue

            excluded_count = 0
            if user_detector is not None:
                model, scaler = user_detector
                train_count = 0
            else:
                known_times = db.scalars(
                    select(Anomaly.timestamp).where(
                        Anomaly.device == device,
                        Anomaly.timestamp >= rows[0].timestamp - ANOMALY_HISTORY_MARGIN,
                    )
                ).all()
                excluded = known_anomaly_mask(ts, cpu, ram, known_times)
                excluded_count = int((excluded & ~recent_mask).sum())

                x_train, _ = training_blocks(ts, cpu, ram, ~recent_mask & ~excluded)
                train_count = len(x_train)
                if train_count < settings.min_points:
                    logger.debug(
                        "%s: not enough clean contiguous points for auto-mode (%d/%d)",
                        device,
                        train_count,
                        settings.min_points,
                    )
                    continue

                model, scaler = fit_detector(x_train)

            scaled = scaler.transform(features[recent_indices])
            predictions = model.predict(scaled)
            scores = model.decision_function(scaled)

            logger.debug(
                "%s | mode=%s | total=%d | train=%d | excluded_known_anomaly=%d | checked=%d | predicted_anomalies=%d",
                device,
                mode,
                len(rows),
                train_count,
                excluded_count,
                len(recent_indices),
                int(np.count_nonzero(predictions == -1)),
            )
            devices_checked += 1

            metric_ids = [rows[i].id for i in recent_indices if rows[i].id is not None]
            existing_ids = (
                set(
                    db.scalars(
                        select(Anomaly.metric_id).where(
                            Anomaly.metric_id.in_(metric_ids)
                        )
                    ).all()
                )
                if metric_ids
                else set()
            )

            for position, index in enumerate(recent_indices):
                if predictions[position] != -1:
                    continue
                score = float(scores[position])
                if score >= settings.score_threshold:
                    continue

                row = rows[index]
                if row.id in existing_ids:
                    continue
                if offline[index]:
                    continue

                reason = _describe_reason(
                    row.cpu, row.ram, *(float(v) for v in features[index, 2:6])
                )
                if reason is None:
                    if row.cpu < WEAK_COMBINED_LIMIT and row.ram < WEAK_COMBINED_LIMIT:
                        continue
                    reason = (
                        f"combined anomaly (cpu={row.cpu:.1f}%, ram={row.ram:.1f}%)"
                    )

                new_anomalies.append(
                    {
                        "metric_id": row.id,
                        "cpu": row.cpu,
                        "ram": row.ram,
                        "timestamp": row.timestamp,
                        "reason": reason,
                        "score": round(score, 4),
                        "device": row.device,
                    }
                )

        if new_anomalies:
            db.execute(
                insert(Anomaly).on_conflict_do_nothing(index_elements=["metric_id"]),
                new_anomalies,
            )
            db.commit()
            logger.info(
                "Saved %d new anomalies across %d checked devices",
                len(new_anomalies),
                devices_checked,
            )

        return {
            "status": "ok",
            "mode": mode,
            "devices_checked": devices_checked,
            "anomalies_found": len(new_anomalies),
        }

    except Exception:
        db.rollback()
        logger.exception("Server error during detect_anomalies")
        return {"status": "error", "error": "Server error"}
    finally:
        db.close()
