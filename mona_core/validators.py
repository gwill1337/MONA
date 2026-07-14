import ipaddress
import re

from pydantic import BaseModel, field_validator

DEVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,15}$")


class DeviceCreate(BaseModel):
    ip: str
    name: str
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return validate_device_name(v)

    @field_validator("ip")
    @classmethod
    def _validate_ip(cls, v: str) -> str:
        return validate_ip_address(v)


# ─── Validation ────────────────────────────────────────────────────────────────
def validate_device_name(name: str) -> str:
    name = name.strip()
    if not DEVICE_NAME_RE.match(name):
        raise ValueError(
            "Name can only contain letters, numbers, '_' and '-' (up to 15 characters)"
        )
    return name


def validate_ip_address(ip: str) -> str:
    ip = ip.strip()
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise ValueError("Must be a valid IPv4 or IPv6 address")
    return ip
