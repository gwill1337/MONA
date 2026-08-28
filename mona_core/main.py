from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from mona_core.config import settings
from mona_core.security import (
    admin_router,
    auth_router,
    seed_admin,
    user_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_admin()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    message = (
        detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": message},
    )


Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Prometheus"])

# ─── API endpoints ──────────────────────────────────────────────────────────
from mona_core.routers import (  # noqa: F401 E402
    dashboard,
    devices,
    health,
    model,
    monitoring,
    tasks,
    users,
)

app.include_router(monitoring.router_prometheus)
app.include_router(health.router)
app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
app.include_router(user_router, prefix="/api/v1", tags=["User"])
app.include_router(auth_router, prefix="/api/v1")
