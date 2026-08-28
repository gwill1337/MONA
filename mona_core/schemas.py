from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict

from mona_core.db import int_pk


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUser(BaseModel):
    username: str
    password: str
    role: Literal["user", "admin"]


class UserGetOut(BaseModel):
    id: int_pk
    username: str
    role: Literal["user", "admin"]

    model_config = ConfigDict(from_attributes=True)


class DeviceOut(BaseModel):
    ip: str
    name: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class AnomalySchema(BaseModel):
    id: int_pk
    metric_id: int
    cpu: float
    ram: float
    timestamp: datetime
    reason: str
    score: float
    detected_at: datetime
    device: str

    model_config = ConfigDict(from_attributes=True)


class DashboardAnomaly(BaseModel):
    id: int_pk
    cpu: float
    ram: float
    timestamp: datetime
    reason: str
    score: float
    device: str

    model_config = ConfigDict(from_attributes=True)


class DashboardMetric(BaseModel):
    timestamp: datetime
    cpu: float
    ram: float
    device: str

    model_config = ConfigDict(from_attributes=True)


class AnomalyOut(BaseModel):
    items: list[AnomalySchema]
    limit: int
    offset: int


class ModelInfo(BaseModel):
    trained_at: datetime
    trained_by: str
    points_count: int
    period_from: Optional[datetime] = None
    period_to: Optional[datetime] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModelInfoOk(BaseModel):
    status: Literal["ok"]
    model: ModelInfo


class ModelInfoEmpty(BaseModel):
    status: Literal["no_model"]
    message: str


ModelInfoOut = Union[ModelInfoOk, ModelInfoEmpty]


class TrainModelOut(BaseModel):
    status: str
    message: str
    task_id: str


class DeleteModelOut(BaseModel):
    status: Literal["ok", "error"] = "ok"
    deleted: int
    message: str


class ChangePassword(BaseModel):
    username: str
    new_password: str


class ChangeRole(BaseModel):
    role: Literal["user", "admin"]


class MessageResponse(BaseModel):
    status: Literal["ok", "error"] = "ok"
    message: str


class MetricSchema(BaseModel):
    id: int_pk
    cpu: float
    ram: float
    device: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricsOut(BaseModel):
    items: list[MetricSchema]
    next_cursor: Optional[datetime]


class TaskStatusOut(BaseModel):
    task_id: str
    state: Optional[str]
    result: Optional[Any]


class DashboardOut(BaseModel):
    devices: list[str]
    model: Optional[ModelInfo]
    metrics: list[DashboardMetric]
    anomalies: list[DashboardAnomaly]


class LoginOut(BaseModel):
    status: Literal["ok"]
    message: str
    role: Literal["user", "admin"]


class MeOut(BaseModel):
    authenticated: bool


class UserSession(BaseModel):
    id: int
    username: str
    role: Literal["user", "admin"]


class LivenessProbe(BaseModel):
    status: Literal["alive"]


class ReadinessProbe(BaseModel):
    status: Literal["ready"]
