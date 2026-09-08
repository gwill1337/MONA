import logging
from typing import Sequence

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mona_core.db import Device
from mona_core.schemas import (
    DeviceOut,
    MessageResponse,
)
from mona_core.security import (
    admin_router,
    get_db,
    user_router,
)
from mona_core.validators import DeviceCreate

# ─── Logger ─────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


@user_router.get("/devices", response_model=list[DeviceOut])
def list_devices(
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> Sequence[Device]:
    query = select(Device).order_by(Device.id).limit(limit).offset(offset)
    return db.scalars(query).all()


@admin_router.post(
    "/devices", status_code=status.HTTP_201_CREATED, response_model=MessageResponse
)
def create_device(body: DeviceCreate, db: Session = Depends(get_db)) -> MessageResponse:
    logger.debug("Attempting to create device", extra={"payload": body.model_dump()})

    dev = Device(ip=body.ip, name=body.name, is_active=body.is_active)
    db.add(dev)
    try:
        db.commit()
        db.refresh(dev)
    except IntegrityError:
        db.rollback()
        logger.warning(
            "Device creating conflict error for device:",
            extra={"ip": body.ip, "device": body.name, "is_active": body.is_active},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Name already exists",
        )
    except Exception:
        db.rollback()
        logger.exception("Error during creating device")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error"
        )
    logger.info(
        "Device created",
        extra={"ip": body.ip, "device": body.name, "is_active": body.is_active},
    )
    return MessageResponse(message="Device created")


@admin_router.delete("/devices/{device_id}", response_model=MessageResponse)
def delete_device(device_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    logger.debug("Attempting to delete device", extra={"device": device_id})
    stmt = delete(Device).where(Device.id == device_id)
    try:
        result = db.execute(stmt)

        if result.rowcount == 0:  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

        db.commit()

        logger.info("Device deleted", extra={"device_id": device_id})
        return MessageResponse(message="Device deleted")
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Error during deleting device")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
