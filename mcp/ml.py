import json
import logging
import pickle as sio
from datetime import UTC, datetime, timedelta

from server import mcp
from sqlalchemy import select

from mona_core.config import settings
from mona_core.db import Metric, SessionLocal, TrainedModel
from mona_core.ml import _build_features

logger = logging.getLogger(__name__)

@mcp.tool()
def train_anomaly_model(hours: float = 24.0, note: str = "Trained via MCP AI") -> str:
    """
    Run training for the anomaly detection model (Isolation Forest) based on historical CPU metrics.
    
    Args:
        hours: Time range in hours to fetch data from (default 24).
        note: Text note or description for the saved model.
    """
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
            return f"Error: Not enough data for training (found {len(rows)} points, minimum 30 required)."

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
            trained_by="mcp-ai-user",
            points_count=len(rows),
            period_from=rows[0].timestamp,
            period_to=rows[-1].timestamp,
            note=note.strip() or None,
        )
        db.add(record)
        db.commit()

        return (
            f"Success! Model successfully trained on {len(rows)} points "
            f"over the last {hours} hours. Note: '{note}'"
        )

    except Exception as e:
        db.rollback()
        logger.exception("Server error during training model via MCP")
        return f"Error during model training: {str(e)}"
    finally:
        db.close()


@mcp.tool()
def get_model_info() -> str:
    """Get metadata about the latest trained MONA model."""
    with SessionLocal() as session:
        model = session.scalar(
            select(TrainedModel)
            .order_by(TrainedModel.trained_at.desc())
            .limit(1)
        )

        if model is None:
            return json.dumps({
                "status": "not_found",
                "message": "No trained models found, using auto mode",
            })

        return json.dumps({
            "status": "success",
            "model": {
                "id": model.id,
                "trained_at": model.trained_at.isoformat(),
                "trained_by": model.trained_by,
                "points_count": model.points_count,
                "period_from": model.period_from.isoformat(),
                "period_to": model.period_to.isoformat(),
                "note": model.note,
            },
        }, ensure_ascii=False)
