import logging

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mona_core.db import Users
from mona_core.schemas import (
    ChangePassword,
    ChangeRole,
    CreateUser,
    MessageResponse,
    UserGetOut,
    UserSession,
)
from mona_core.security import (
    admin_router,
    get_current_user,
    get_db,
    remove_all_sessions,
)

# ─── Logger ─────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


@admin_router.get("/users", response_model=list[UserGetOut])
def get_users(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[UserGetOut]:
    query = select(Users).order_by(Users.id).limit(limit).offset(offset)
    res = db.execute(query).scalars().all()
    return [UserGetOut.model_validate(u) for u in res]


@admin_router.post("/user", response_model=MessageResponse)
def create_user(
    body: CreateUser,
    db: Session = Depends(get_db),
) -> MessageResponse:
    logger.debug("Attempting to create a new user")
    user = Users(username=body.username, role=body.role)
    user.set_password(body.password)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        logger.warning("User creation conflict error")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    except Exception:
        logger.exception("Server Error during user creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error"
        )

    logger.info("User created", extra={"username": body.role, "role": body.role})
    return MessageResponse(message="User created")


@admin_router.delete("/user/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user_to_delete = db.execute(
        select(Users).where(Users.id == user_id)
    ).scalar_one_or_none()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_to_delete.role == "admin":
        admin_count = db.execute(
            select(func.count()).select_from(Users).where(Users.role == "admin")
        ).scalar_one()
        if admin_count <= 1:
            logger.warning("Attempting to delete the last remaining admin")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last remaining admin",
            )

    db.delete(user_to_delete)
    try:
        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Server error during user deletion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )

    await remove_all_sessions(user_id)

    logger.info("User deleted", extra={"user_id": user_id})
    return MessageResponse(message="User deleted")


@admin_router.patch("/user/change-password", response_model=MessageResponse)
def change_user_password(
    body: ChangePassword,
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not body.new_password.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password is required",
        )

    query = select(Users).where(Users.username == body.username)
    res = db.execute(query).scalar_one_or_none()
    if not res:
        logger.warning("User not found for changing user password")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Username invalid",
        )
    res.set_password(body.new_password)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Server error during password changing", extra={"username": body.username}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
    logger.info("Password changed for user", extra={"username": body.username})
    return MessageResponse(message="Password changed")


@admin_router.patch("/user/{user_id}/role", response_model=MessageResponse)
def change_user_role(
    user_id: int,
    body: ChangeRole,
    db: Session = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> MessageResponse:
    stmt = select(Users).where(Users.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        logger.warning("User not found for role changing")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "User not found"},
        )

    if user.username == current_user.username:
        logger.warning(
            "Attempting to change role to own role", extra={"username": user.username}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own role",
        )
    elif user.role == body.role:
        logger.info("Role unchanged", extra={"username": user.username})
        return MessageResponse(message="Role unchanged")
    elif user.role == "admin" and body.role == "user":
        admin_count = db.execute(
            select(func.count()).select_from(Users).where(Users.role == "admin")
        ).scalar_one()
        if admin_count <= 1:
            logger.warning(
                "Attempting to demote the last remaining admin",
                extra={"username": user.username},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining admin",
            )

    user.role = body.role
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception("Server error during role changing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
    logger.info("Role switched", extra={"username": user.username})
    return MessageResponse(message="Role switched")
