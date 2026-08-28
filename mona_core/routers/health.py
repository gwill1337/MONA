from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.orm import Session

from mona_core.schemas import LivenessProbe, ReadinessProbe
from mona_core.security import (
    get_db,
    redis_client,
)

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def liveness_probe() -> LivenessProbe:
    return LivenessProbe(status="alive")


@router.get("/health/ready")
async def readiness_probe(
    db: Session = Depends(get_db),
) -> ReadinessProbe:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    try:
        await redis_client.ping()
    except RedisError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable",
        )

    return ReadinessProbe(status="ready")
