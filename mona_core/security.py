import json
import os
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mona_core.config import redis_client, settings
from mona_core.db import SessionLocal, Users
from mona_core.schemas import (
    LoginOut,
    LoginRequest,
    MeOut,
    MessageResponse,
    UserSession,
)


# ─── helpers ────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Sessions ───────────────────────────────────────────────────────────────


def _user_sessions_key(user_id: int) -> str:
    return f"user_sessions:{user_id}"


async def register_sesion(user_id: int, session_id: str) -> None:
    key = _user_sessions_key(user_id)
    await redis_client.sadd(key, session_id)
    await redis_client.expire(key, settings.session_ttl)


async def unregister_session(user_id: int, session_id: str) -> None:
    await redis_client.srem(_user_sessions_key(user_id), session_id)


async def remove_all_sessions(user_id: int) -> None:
    key = _user_sessions_key(user_id)
    session_ids = await redis_client.smembers(key)
    if session_ids:
        await redis_client.delete(*[f"session:{sid}" for sid in session_ids])  # type: ignore[str-bytes-safe]
    await redis_client.delete(key)


# ─── Startup ────────────────────────────────────────────────────────────────
def _read_pair_list(
    usernames_env: str, passwords_env: str
) -> tuple[list[str], list[str]]:
    usernames = [
        u.strip() for u in os.getenv(usernames_env, "").split(",") if u.strip()
    ]
    passwords = [
        p.strip() for p in os.getenv(passwords_env, "").split(",") if p.strip()
    ]
    return usernames, passwords


def _seed_role(
    usernames: list[str], passwords: list[str], role: str, db: Session
) -> None:
    if len(usernames) != len(passwords):
        print(
            f"Warning: mismatched username/password count for role '{role}', skipping"
        )
        return
    for username, password in zip(usernames, passwords):
        exists = db.execute(
            select(Users).where(Users.username == username)
        ).scalar_one_or_none()
        if not exists:
            account = Users(username=username, role=role)
            account.set_password(password)
            db.add(account)


def seed_admin() -> None:
    admin_usernames, admin_passwords = _read_pair_list(
        "ADMIN_USERNAMES", "ADMIN_PASSWORDS"
    )
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


# ─── limiter ────────────────────────────────────────────────────────────────
async def check_rate_limit(
    key: str,
    max_attempts: int = settings.max_attempts,
    window: int = settings.lockout_seconds,
):
    attempts_key = f"login_attempts:{key}"
    attempts = await redis_client.incr(attempts_key)
    if attempts == 1:
        await redis_client.expire(attempts_key, window)

    if attempts > max_attempts:
        ttl = await redis_client.ttl(attempts_key)
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {ttl} seconds",
        )


async def reset_rate_limit(key: str):
    await redis_client.delete(f"login_attempts:{key}")


# ─── Auth ───────────────────────────────────────────────────────────────────
async def get_current_user(user_session: str | None = Cookie(None)) -> UserSession:
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not auth(Cokie not found)",
        )

    raw = await redis_client.get(f"session:{user_session}")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or not valid",
        )

    data = json.loads(raw)
    return UserSession.model_validate(data)


async def require_admin(user: UserSession = Depends(get_current_user)) -> UserSession:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user


user_router = APIRouter(dependencies=[Depends(get_current_user)])
admin_router = APIRouter(dependencies=[Depends(require_admin)])

# ─── Auth endpoints ─────────────────────────────────────────────────────────
auth_router = APIRouter(tags=["Auth"])


# ─── login & logout ─────────────────────────────────────────────────────────
@auth_router.post("/auth/login", tags=["Auth"], response_model=LoginOut)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginOut:
    ip = request.client.host if request.client else "127.0.0.1"

    await check_rate_limit(f"ip:{ip}")
    await check_rate_limit(f"user:{body.username}")

    stmt = select(Users).where(Users.username == body.username)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not user.check_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    await reset_rate_limit(f"ip:{ip}")
    await reset_rate_limit(f"user:{body.username}")

    session_id = secrets.token_urlsafe(32)
    session_data = json.dumps(
        {"id": user.id, "username": user.username, "role": user.role}
    )
    await redis_client.set(
        f"session:{session_id}", session_data, ex=settings.session_ttl
    )
    await register_sesion(user.id, session_id)

    response.set_cookie(
        key="user_session",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=43200,
    )
    return LoginOut(status="ok", message="Successfully login", role=user.role)


@auth_router.post("/auth/logout", tags=["Auth"], response_model=MessageResponse)
async def logout(
    response: Response, user_session: str | None = Cookie(None)
) -> MessageResponse:
    if user_session:
        raw = await redis_client.get(f"sesion:{user_session}")
        if raw:
            data = json.loads(raw)
            await unregister_session(data["id"], user_session)
        await redis_client.delete(f"session:{user_session}")

    response.delete_cookie("user_session")
    return MessageResponse(message="logged out")


@auth_router.get("/auth/me", response_model=MeOut)
async def auth_me(admin=Depends(get_current_user)) -> MeOut:
    return MeOut(authenticated=True)
