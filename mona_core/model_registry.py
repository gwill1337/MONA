from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.orm import Session

from mona_core.db import TrainedModel

USER = "user"


def _rowcount(result: Any) -> int:
    return cast(CursorResult[Any], result).rowcount or 0


def list_models(db: Session) -> list[TrainedModel]:
    """All manually trained models, newest first (model_data is deferred)."""
    stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == USER)
        .order_by(TrainedModel.trained_at.desc(), TrainedModel.id.desc())
    )
    return list(db.scalars(stmt).all())


def get_active(db: Session) -> TrainedModel | None:
    """The model used by anomaly detection, or None (= auto-mode)."""
    stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == USER, TrainedModel.is_active.is_(True))
        .order_by(TrainedModel.trained_at.desc(), TrainedModel.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def deactivate_all(db: Session) -> int:
    """Switch to auto-mode without deleting anything."""
    result = db.execute(
        update(TrainedModel)
        .where(TrainedModel.is_active.is_(True))
        .values(is_active=False)
    )
    return _rowcount(result)


def activate(db: Session, model_id: int) -> bool:
    """Make `model_id` the active model. False if it does not exist."""
    found = db.scalar(
        select(TrainedModel.id).where(
            TrainedModel.id == model_id, TrainedModel.trained_by == USER
        )
    )
    if found is None:
        return False
    deactivate_all(db)
    db.execute(
        update(TrainedModel).where(TrainedModel.id == model_id).values(is_active=True)
    )
    return True


def delete_one(db: Session, model_id: int) -> tuple[bool, bool]:
    """Delete one model. Returns (deleted, was_active)."""
    row = db.execute(
        select(TrainedModel.id, TrainedModel.is_active).where(
            TrainedModel.id == model_id, TrainedModel.trained_by == USER
        )
    ).first()
    if row is None:
        return False, False
    db.execute(delete(TrainedModel).where(TrainedModel.id == model_id))
    return True, bool(row.is_active)


def prune(db: Session, keep: int) -> int:
    """Keep the `keep` newest models (plus the active one); delete the rest."""
    newest = (
        select(TrainedModel.id)
        .where(TrainedModel.trained_by == USER)
        .order_by(TrainedModel.trained_at.desc(), TrainedModel.id.desc())
        .limit(keep)
    )
    result = db.execute(
        delete(TrainedModel).where(
            TrainedModel.trained_by == USER,
            TrainedModel.is_active.is_(False),
            TrainedModel.id.not_in(newest),
        )
    )
    return _rowcount(result)
