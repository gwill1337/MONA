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
    user = Users(username=body.username, role=body.role)
    user.set_password(body.password)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last remaining admin",
            )

    db.delete(user_to_delete)
    try:
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    await remove_all_sessions(user_id)

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
        # log Warn
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Username or Password invalid",
        )
    res.set_password(body.new_password)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": "User not found"},
        )

    if user.role == body.role:
        return MessageResponse(message="Role unchanged")
    elif user.role == "admin" and body.role == "user":
        admin_count = db.execute(
            select(func.count()).select_from(Users).where(Users.role == "admin")
        ).scalar_one()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining admin",
            )
    elif user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own role",
        )

    user.role = body.role
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error",
        )
    return MessageResponse(message="Role switched")
