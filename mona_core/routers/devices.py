from typing import Sequence

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import delete, select
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
    dev = Device(ip=body.ip, name=body.name, is_active=body.is_active)
    db.add(dev)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Name already exists",
        )
    db.refresh(dev)
    return MessageResponse(message="Device created")


@admin_router.delete("/devices/{device_id}", response_model=MessageResponse)
def delete_device(device_id: int, db: Session = Depends(get_db)) -> MessageResponse:
    stmt = delete(Device).where(Device.id == device_id)
    try:
        result = db.execute(stmt)

        if result.rowcount == 0:  # type: ignore
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

        db.commit()

        return MessageResponse(message="Device deleted")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
