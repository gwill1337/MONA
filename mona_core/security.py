import json
import os
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from redis.asyncio import from_url
from sqlalchemy import select
from sqlalchemy.orm import Session

from mona_core.db import SessionLocal, Users

redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = from_url(redis_url, decode_responses=True)


# ─── helpers ────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginRequest(BaseModel):
    username: str
    password: str


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


def seed_admin():
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

# ─── Auth endpoints ───────────────────────────────────────────────────────────
auth_router = APIRouter(tags=["Auth"])


# ─── login & logout ─────────────────────────────────────────────────────────
@auth_router.post("/api/auth/login", tags=["Auth"])
async def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    stmt = select(Users).where(Users.username == body.username)
    admin = db.execute(stmt).scalar_one_or_none()

    if not admin or not admin.check_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_id = secrets.token_urlsafe(32)
    session_data = json.dumps(
        {"id": admin.id, "username": admin.username, "role": admin.role}
    )
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


@auth_router.post("/api/auth/logout", tags=["Auth"])
async def logout(response: Response, user_session: str | None = Cookie(None)):
    if user_session:
        await redis_client.delete(f"session:{user_session}")

    response.delete_cookie("user_session")
    return {"status": "ok", "message": "Successfuly logout"}


@auth_router.get("/api/auth/me")
async def auth_me(admin=Depends(get_current_user)):
    return {"authenticated": True}
