from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mona_core.config import celery_client
from mona_core.db import Anomaly, TrainedModel
from mona_core.schemas import (
    AnomalyOut,
    AnomalySchema,
    DeleteModelOut,
    ModelInfo,
    ModelInfoEmpty,
    ModelInfoOk,
    ModelInfoOut,
    TrainModelOut,
)
from mona_core.security import (
    admin_router,
    get_db,
    user_router,
)


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


@user_router.get("/model-info", response_model=ModelInfoOut)
def model_info(db: Session = Depends(get_db)) -> ModelInfoOut:
    stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    )

    record = db.execute(stmt).scalar_one_or_none()

    if record is None:
        return ModelInfoEmpty(
            status="no_model",
            message="Model is not manually trained yet. Using auto-mode.",
        )
    model_data = ModelInfo.model_validate(record)
    return ModelInfoOk(status="ok", model=model_data)


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
) -> TrainModelOut:

    task = celery_client.send_task(
        "tasks.train_model_task", kwargs={"hours": hours, "note": note}
    )

    return TrainModelOut(
        status="accepted",
        message="Model training task has been submitted to the background.",
        task_id=task.id,
    )


@admin_router.delete("/model", response_model=DeleteModelOut)
def delete_model(db: Session = Depends(get_db)) -> DeleteModelOut:
    """Deletes the custom model — Celery will return to auto-mode."""
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
            message="Model deleted. Celery switched to auto-mode.",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
