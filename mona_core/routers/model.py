import logging
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mona_core import model_registry as registry
from mona_core.config import celery_client
from mona_core.db import Anomaly, TrainedModel
from mona_core.schemas import (
    AnomalyOut,
    AnomalySchema,
    DeleteModelOut,
    MessageResponse,
    ModelInfo,
    ModelInfoEmpty,
    ModelInfoOk,
    ModelInfoOut,
    ModelListOut,
    TrainModelOut,
)
from mona_core.security import (
    admin_router,
    get_db,
    user_router,
)

# ─── Logger ─────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


@user_router.get("/anomalies", response_model=AnomalyOut)
def get_anomalies(
    hours: int = 24,
    device: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AnomalyOut:
    stmt = select(Anomaly)
    if device:
        stmt = stmt.where(Anomaly.device == device)
    if hours > 0:
        stmt = stmt.where(
            Anomaly.timestamp >= datetime.now(UTC) - timedelta(hours=hours)
        )

    stmt = stmt.order_by(Anomaly.timestamp.desc()).limit(limit).offset(offset)
    anomalies = db.execute(stmt).scalars().all()

    return AnomalyOut(
        items=[AnomalySchema.model_validate(a) for a in anomalies],
        limit=limit,
        offset=offset,
    )


# ─── Models ─────────────────────────────────────────────────────────────────


@user_router.get("/model-info", response_model=ModelInfoOut)
def model_info(db: Session = Depends(get_db)) -> ModelInfoOut:
    """The ACTIVE model (the one anomaly detection uses)."""
    record = registry.get_active(db)

    if record is None:
        return ModelInfoEmpty(
            status="no_model",
            message="No active model. Using auto-mode.",
        )
    return ModelInfoOk(status="ok", model=ModelInfo.model_validate(record))


@user_router.get("/models", response_model=ModelListOut)
def list_models(db: Session = Depends(get_db)) -> ModelListOut:
    """All saved models, newest first."""
    return ModelListOut(
        items=[ModelInfo.model_validate(m) for m in registry.list_models(db)]
    )


@admin_router.post(
    "/train", status_code=status.HTTP_202_ACCEPTED, response_model=TrainModelOut
)
def train_model(
    hours: float = Query(
        default=1.0,
        ge=0,
        le=24 * 7,
        description="Hours of recent data to use for training",
    ),
    note: str = Query(default="", description="Comment (optional)"),
    activate: bool = Query(
        default=True,
        description="Make the new model active (false = just save it)",
    ),
) -> TrainModelOut:

    task = celery_client.send_task(
        "tasks.train_model_task",
        kwargs={"hours": hours, "note": note, "activate": activate},
    )

    return TrainModelOut(
        status="accepted",
        message="Model training task has been submitted to the background.",
        task_id=task.id,
    )


@admin_router.post("/models/deactivate", response_model=MessageResponse)
def deactivate_models(db: Session = Depends(get_db)) -> MessageResponse:
    """Switch to auto-mode. Saved models are kept."""
    try:
        registry.deactivate_all(db)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Server error during switching to auto-mode")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
    return MessageResponse(message="Switched to auto-mode.")


@admin_router.post("/models/{model_id}/activate", response_model=MessageResponse)
def activate_model(model_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    try:
        if not registry.activate(db, model_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Server error during model activation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
    return MessageResponse(message="Model activated.")


@admin_router.delete("/models/{model_id}", response_model=DeleteModelOut)
def delete_one_model(model_id: int, db: Session = Depends(get_db)) -> DeleteModelOut:
    """If it was active, the system falls back to auto-mode."""
    try:
        deleted, was_active = registry.delete_one(db, model_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Server error during model deletion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
    return DeleteModelOut(
        status="ok",
        deleted=1,
        message="Model deleted. Switched to auto-mode."
        if was_active
        else "Model deleted.",
    )


@admin_router.delete("/model", response_model=DeleteModelOut)
def delete_model(db: Session = Depends(get_db)) -> DeleteModelOut:
    """Deletes ALL custom models — Celery will return to auto-mode."""
    try:
        stmt = delete(TrainedModel).where(TrainedModel.trained_by == "user")
        result = db.execute(stmt)
        db.commit()
        deleted = result.rowcount if result.rowcount else 0  # type: ignore
        if deleted == 0:
            return DeleteModelOut(
                status="ok", deleted=deleted, message="No model to delete."
            )
        return DeleteModelOut(
            status="ok",
            deleted=deleted,
            message="Models deleted. Celery switched to auto-mode.",
        )

    except Exception:
        db.rollback()
        logger.exception("Server error during deletion the models")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
