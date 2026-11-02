import json
import logging

from server import mcp
from sqlalchemy import func, select

from mona_core import model_registry as registry
from mona_core.config import celery_client
from mona_core.db import SessionLocal, TrainedModel

logger = logging.getLogger(__name__)


def _model_dict(m: TrainedModel) -> dict:
    return {
        "id": m.id,
        "is_active": m.is_active,
        "trained_at": m.trained_at.isoformat(),
        "trained_by": m.trained_by,
        "points_count": m.points_count,
        "period_from": m.period_from.isoformat(),
        "period_to": m.period_to.isoformat(),
        "note": m.note,
    }


@mcp.tool()
def train_anomaly_model(
    hours: float = 1.0,
    note: str = "Trained via MCP AI",
    activate: bool = True,
) -> str:
    """
    Submit a background training job for the anomaly detection model
    (Isolation Forest). Uses the same Celery task as the web UI.

    Training is asynchronous: this tool only submits the job and returns a
    task_id. Use get_task_status(task_id) to follow it.

    Train on a period of normal load: anomalies inside the training window
    become part of what the model considers "normal".

    Only call this when the user explicitly asks for training.

    Args:
        hours: Hours of recent data to train on (0-168, default 1).
        note: Text note or description for the saved model.
        activate: If true (default) the new model becomes the active one used
            by anomaly detection. If false it is only saved; it can be
            activated later with activate_model.
    """
    if not 0 < hours <= 24 * 7:
        return json.dumps(
            {"status": "error", "message": "hours must be > 0 and <= 168"}
        )

    try:
        task = celery_client.send_task(
            "tasks.train_model_task",
            kwargs={"hours": hours, "note": note.strip(), "activate": activate},
        )
    except Exception:
        logger.exception("Failed to submit training task via MCP")
        return json.dumps(
            {"status": "error", "message": "Unable to submit training task"}
        )

    logger.info("Training task %s submitted via MCP (hours=%s)", task.id, hours)
    return json.dumps(
        {
            "status": "accepted",
            "message": "Model training task has been submitted to the background.",
            "task_id": task.id,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def get_task_status(task_id: str) -> str:
    """Get the state of a background task (e.g. model training).

    States: PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED.
    PENDING can also mean the task id is unknown.
    """
    try:
        result = celery_client.AsyncResult(task_id)
        payload: dict = {"task_id": task_id, "state": result.state}
        if result.state == "SUCCESS":
            payload["result"] = result.result
        elif result.state in ("FAILURE", "REVOKED"):
            payload["error"] = str(result.result)
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        logger.exception("Failed to get task status via MCP")
        return json.dumps(
            {"status": "error", "message": "Unable to get task status"}
        )


@mcp.tool()
def get_model_info() -> str:
    """Get metadata about the ACTIVE MONA model (the one anomaly detection uses).

    Also returns how many manually trained models are stored.
    status "no_model" means the system runs in auto-mode.
    """
    with SessionLocal() as session:
        stored = session.scalar(
            select(func.count())
            .select_from(TrainedModel)
            .where(TrainedModel.trained_by == registry.USER)
        )
        model = registry.get_active(session)

        if model is None:
            return json.dumps({
                "status": "no_model",
                "message": "No active model. Using auto-mode.",
                "models_stored": stored or 0,
            })

        return json.dumps({
            "status": "ok",
            "models_stored": stored or 0,
            "model": _model_dict(model),
        }, ensure_ascii=False)


@mcp.tool()
def list_models() -> str:
    """List all saved manually trained models, newest first.

    Each item has an id, is_active flag, training period, point count and note.
    """
    with SessionLocal() as session:
        models = registry.list_models(session)
        return json.dumps(
            {"count": len(models), "items": [_model_dict(m) for m in models]},
            ensure_ascii=False,
        )


@mcp.tool()
def activate_model(model_id: int) -> str:
    """Make a saved model the active one used by anomaly detection.

    Takes effect on the next detection run. Only call this when the user
    explicitly asks to switch models. Get ids from list_models.
    """
    with SessionLocal() as session:
        try:
            if not registry.activate(session, model_id):
                return json.dumps(
                    {"status": "error", "message": "Model not found"}
                )
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to activate model via MCP")
            return json.dumps(
                {"status": "error", "message": "Failed to activate model"}
            )

    logger.info("Model %s activated via MCP", model_id)
    return json.dumps({"status": "ok", "message": f"Model {model_id} activated"})


@mcp.tool()
def deactivate_model() -> str:
    """Switch anomaly detection to auto-mode. Saved models are kept.

    Only call this when the user explicitly asks for it.
    """
    with SessionLocal() as session:
        try:
            registry.deactivate_all(session)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to switch to auto-mode via MCP")
            return json.dumps(
                {"status": "error", "message": "Failed to switch to auto-mode"}
            )

    logger.info("Switched to auto-mode via MCP")
    return json.dumps({"status": "ok", "message": "Switched to auto-mode"})
