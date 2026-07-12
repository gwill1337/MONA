import json
import os
import secrets
import re
import ipaddress
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from celery import Celery
from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, field_validator
from redis.asyncio import from_url
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from mona_core.db import (
    Users,
    Anomaly,
    Base,
    Device,
    Metric,
    SessionLocal,
    TrainedModel,
    engine,
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed_admin()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:30081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
celery_client = Celery("mona", broker=redis_url, backend=redis_url)

redis_client = from_url(redis_url, decode_responses=True)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ─── helpers ────────────────────────────────────────────────────────────────
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


class LoginRequest(BaseModel):
    username: str
    password: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DEVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,15}$")

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
# ─── Startup ────────────────────────────────────────────────────────────────
def _read_pair_list(usernames_env: str, passwords_env: str) -> tuple[list[str], list[str]]:
    usernames = [u.strip() for u in os.getenv(usernames_env, "").split(",") if u.strip()]
    passwords = [p.strip() for p in os.getenv(passwords_env, "").split(",") if p.strip()]
    return usernames, passwords

def _seed_role(usernames: list[str], passwords: list[str], role: str, db: Session) -> None:
    if len(usernames) != len(passwords):
        print(f"Warning: mismatched username/password count for role '{role}', skipping")
        return
    for username, password in zip(usernames, passwords):
        exists = db.execute(select(Users).where(Users.username == username)).scalar_one_or_none()
        if not exists:
            account = Users(username=username, role=role)
            account.set_password(password)
            db.add(account)

def seed_admin():
    admin_usernames, admin_passwords = _read_pair_list("ADMIN_USERNAMES", "ADMIN_PASSWORDS")
    user_usernames, user_passwords = _read_pair_list("USER_USERNAMES", "USER_PASSWORDS")

    if not admin_usernames and not user_usernames:
        return

    with SessionLocal() as db:
        try:
            _seed_role(admin_usernames, admin_passwords, "admin", db)
            _seed_role(user_usernames, user_passwords, "user", db)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")


# ─── Auth ────────────────────────────────────────────────────────────────
async def get_current_user(user_session: str | None = Cookie(None)) -> dict:
    if not user_session:
        raise HTTPException(status_code=401, detail="You are not auth(Cokie not found)")

    raw = await redis_client.get(f"session:{user_session}")
    if not raw:
        raise HTTPException(status_code=401, detail="Session expired or not valid")

    return json.loads(raw)


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

user_router = APIRouter(dependencies=[Depends(get_current_user)])
admin_router = APIRouter(dependencies=[Depends(require_admin)])


# ─── API endpoints ──────────────────────────────────────────────────────────
# ─── Probes (Liveness & Readiness) ──────────────────────────────────────────
@app.get("/health/live", tags=["Health"])
def liveness_probe():
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def readiness_probe(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


# ─── login & logout ─────────────────────────────────────────────────────────
@app.post("/api/auth/login", tags=["Auth"])
async def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    stmt = select(Users).where(Users.username == body.username)
    admin = db.execute(stmt).scalar_one_or_none()

    if not admin or not admin.check_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_id = secrets.token_urlsafe(32)
    session_data = json.dumps({"id": admin.id, "username": admin.username, "role": admin.role})
    await redis_client.set(f"session:{session_id}", session_data, ex=43200)

    response.set_cookie(
        key="user_session",
        value=session_id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=43200,
    )
    return {"status": "ok", "message": "Successfully login", "role": admin.role}


@app.post("/api/auth/logout", tags=["Auth"])
async def logout(response: Response, user_session: str | None = Cookie(None)):
    if user_session:
        await redis_client.delete(f"session:{user_session}")

    response.delete_cookie("user_session")
    return {"status": "ok", "message": "Successfuly logout"}


@app.get("/api/auth/me")
async def auth_me(admin=Depends(get_current_user)):
    return {"authenticated": True}


# ─── Devices ────────────────────────────────────────────────────────────────


@user_router.get("/devices")
def list_devices(db: Session = Depends(get_db)):
    stmt = select(Device)
    return db.execute(stmt).scalars().all()


@admin_router.post("/devices", status_code=201)
def create_device(body: DeviceCreate, db: Session = Depends(get_db)):
    dev = Device(ip=body.ip, name=body.name, is_active=body.is_active)
    db.add(dev)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Name already exists")
    db.refresh(dev)
    return dev


@admin_router.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    stmt = delete(Device).where(Device.id == device_id)
    try:
        result = db.execute(stmt)

        if result.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=404, detail="Device not found")

        db.commit()

        return {"message": "Device deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/prometheus/targets")
def get_prometheus_targets(db: Session = Depends(get_db)):
    stmt = select(Device).where(Device.is_active, Device.ip.is_not(None))
    devices = db.execute(stmt).scalars().all()

    targets = []
    for dev in devices:
        targets.append(
            {
                "targets": [f"{dev.ip}:9100"],
                "labels": {
                    "job": dev.name,
                    "physical_pc": "true",
                    "device_label": dev.name,
                },
            }
        )
    return targets


# ─── Model ──────────────────────────────────────────────────────────────────
@user_router.get("/anomalies")
def get_anomalies(
    hours: int = 24,
    device: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Anomaly)
    if device:
        stmt = stmt.where(Anomaly.device == device)
    if hours > 0:
        stmt = stmt.where(
            Anomaly.timestamp >= datetime.now(UTC) - timedelta(hours=hours)
        )

    stmt = stmt.order_by(Anomaly.timestamp.desc()).limit(limit).offset(offset)
    anomalies = db.execute(stmt).scalars().all()
    return {
        "items": [
            {
                "id": a.id,
                "metric_id": a.metric_id,
                "cpu": a.cpu,
                "ram": a.ram,
                "timestamp": a.timestamp,
                "reason": a.reason,
                "score": a.score,
                "detected_at": a.detected_at,
                "device": a.device,
            }
            for a in anomalies
        ],
        "limit": limit,
        "offset": offset,
    }


@user_router.get("/model-info")
def model_info(db: Session = Depends(get_db)):
    stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    )

    record = db.execute(stmt).scalar_one_or_none()

    if record is None:
        return {
            "status": "no_model",
            "message": "Model is not manually trained yet. Using auto-mode.",
        }
    return {
        "status": "ok",
        "model": {
            "trained_at": record.trained_at,
            "trained_by": record.trained_by,
            "points_count": record.points_count,
            "period_from": record.period_from,
            "period_to": record.period_to,
            "note": record.note,
        },
    }


@admin_router.post("/train", status_code=202)
def train_model(
    hours: float = Query(
        default=1.0,
        ge=0,
        le=24 * 7,
        description="Hours of recent data to use for training",
    ),
    note: str = Query(default="", description="Comment (optional)"),
):

    task = celery_client.send_task(
        "tasks.train_model_task", kwargs={"hours": hours, "note": note}
    )

    return {
        "status": "accepted",
        "message": "Model training task has been submitted to the background.",
        "task_id": task.id,
    }


@admin_router.delete("/model")
def delete_model(db: Session = Depends(get_db)):
    """Deletes the custom model — Celery will return to auto-mode."""
    try:
        stmt = delete(TrainedModel).where(TrainedModel.trained_by == "user")
        result = db.execute(stmt)
        db.commit()
        return {
            "status": "ok",
            "deleted": result.rowcount,  # type: ignore
            "message": "Model deleted. Celery switched to auto-mode.",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")


# ─── Dashboard ──────────────────────────────────────────────────────────────
@user_router.get("/api/dashboard")
def get_dashboard_data(
    hours: int = 1,
    device: str | None = None,
    max_points: int = Query(default=2000, le=10000),
    db: Session = Depends(get_db),
):
    devices_stmt = select(Metric.device).distinct()
    devices = db.execute(devices_stmt).scalars().all()

    since = datetime.now(UTC) - timedelta(hours=hours) if hours > 0 else None

    stmt_m = select(Metric)
    stmt_a = select(Anomaly)

    if device:
        stmt_m = stmt_m.where(Metric.device == device)
        stmt_a = stmt_a.where(Anomaly.device == device)
    if since:
        stmt_m = stmt_m.where(Metric.timestamp >= since)
        stmt_a = stmt_a.where(Anomaly.timestamp >= since)

    stmt_m = stmt_m.order_by(Metric.timestamp.desc()).limit(max_points)
    stmt_a = stmt_a.order_by(Anomaly.timestamp.desc()).limit(max_points)

    metrics = list(reversed(db.execute(stmt_m).scalars().all()))
    anomalies = list(reversed(db.execute(stmt_a).scalars().all()))

    model_stmt = (
        select(TrainedModel)
        .where(TrainedModel.trained_by == "user")
        .order_by(TrainedModel.trained_at.desc())
        .limit(1)
    )
    model_record = db.execute(model_stmt).scalar_one_or_none()

    model_info = None
    if model_record:
        model_info = {
            "trained_at": model_record.trained_at.isoformat(),
            "points_count": model_record.points_count,
            "period_from": model_record.period_from.isoformat()
            if model_record.period_from
            else None,
            "period_to": model_record.period_to.isoformat()
            if model_record.period_to
            else None,
            "note": model_record.note,
        }

    return {
        "devices": devices,
        "model": model_info,
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu": m.cpu,
                "ram": m.ram,
                "device": m.device,
            }
            for m in metrics
        ],
        "anomalies": [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "cpu": a.cpu,
                "ram": a.ram,
                "reason": a.reason,
                "score": a.score,
                "device": a.device,
            }
            for a in anomalies
        ],
    }


# ─── Metrics ────────────────────────────────────────────────────────────────
@user_router.get("/db-metrics")
def get_metrics(
    device: str | None = None,
    hours: int = Query(default=1, le=24 * 7),
    before: datetime | None = None,
    limit: int = Query(default=500, le=5000),
    db: Session = Depends(get_db),
):
    since = datetime.now(UTC) - timedelta(hours=hours)
    stmt = select(Metric).where(Metric.timestamp >= since)
    if device:
        stmt = stmt.where(Metric.device == device)
    if before:
        stmt = stmt.where(Metric.timestamp < before)
    stmt = stmt.order_by(Metric.timestamp.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    next_cursor = rows[-1].timestamp if len(rows) == limit else None
    return {"items": rows, "next_cursor": next_cursor}


# ─── Tasks ──────────────────────────────────────────────────────────────────
@user_router.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    result = celery_client.AsyncResult(task_id)

    raw = None
    if result.ready():
        try:
            raw = result.result
            if isinstance(raw, Exception):
                raw = {"error": str(raw)}
        except Exception:
            raw = None

    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.ready() else None,
    }


app.include_router(admin_router)
app.include_router(user_router)