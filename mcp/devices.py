import json
import logging

from server import mcp
from sqlalchemy import delete, select

from mona_core.db import Device, SessionLocal
from mona_core.schemas import MessageResponse
from mona_core.validators import DeviceCreate

logger = logging.getLogger(__name__)

@mcp.tool()
def get_mona_devices() -> str:
    """Get mona devices from database"""
    with SessionLocal() as session:
        devices = session.scalars(select(Device)).all()

        return json.dumps(
            [
                {"id": d.id, "name": d.name, "ip": d.ip}
                for d in devices
            ],
            ensure_ascii=False,
        )

@mcp.tool()
def add_mona_device(name: str, ip: str, is_active: bool = True) -> MessageResponse:
    """Add a new device to the MONA database."""
    try:
        device_data = DeviceCreate(name=name, ip=ip, is_active=is_active)
    except ValueError:
        return MessageResponse(status="error", message="validation error")

    with SessionLocal() as session:
        existing = session.query(Device).filter((Device.name == device_data.name) | (Device.ip == device_data.ip)).first()
        if existing:
            return MessageResponse(status="error", message="Conflict error, device already exists")

        new_device = Device(
            name=device_data.name,
            ip=device_data.ip,
            is_active=device_data.is_active
        )
        session.add(new_device)
        try:
            session.commit()
            logger.info(f"Device {ip} {name} was created via MCP")
            return MessageResponse(message="Device created")
        except Exception:
            session.rollback()
            return MessageResponse(status="error", message="Server Error 500")

@mcp.tool()
def remove_mona_device(ip: str) -> MessageResponse:
    """Remove a device from the MONA database."""
    with SessionLocal() as session:
        try:
            result = session.execute(
                delete(Device).where(Device.ip == ip)
            )

            if result.rowcount == 0:  # type: ignore
                return MessageResponse(
                    status="error",
                    message="Device not found",
                )

            session.commit()
            logger.info("Device %s removed via MCP", ip)

            return MessageResponse(
                message=f"Device {ip} was removed",
            )

        except Exception:
            session.rollback()
            logger.exception("Failed to remove device via MCP")
            return MessageResponse(
                status="error",
                message="Failed to remove device",
            )
