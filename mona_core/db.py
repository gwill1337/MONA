import os
from datetime import UTC, datetime
from typing import Annotated

import bcrypt
from sqlalchemy import (
    Index,
    LargeBinary,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE = os.getenv("DATABASE_URL", "postgresql://myuser:1234@localhost:5432/mydb")

engine = create_engine(DATABASE)
SessionLocal = sessionmaker(bind=engine)

int_pk = Annotated[int, mapped_column(primary_key=True)]


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int_pk]
    ip: Mapped[str]
    name: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int_pk]
    cpu: Mapped[float]
    ram: Mapped[float]
    device: Mapped[str] = mapped_column(default="default")
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    __table_args__ = (Index("idx_metrics_device_timestamp", "device", "timestamp"),)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int_pk]
    metric_id: Mapped[int]
    cpu: Mapped[float]
    ram: Mapped[float]
    timestamp: Mapped[datetime]
    reason: Mapped[str]
    score: Mapped[float]
    device: Mapped[str]
    detected_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    __table_args__ = (Index("idx_anomalies_device_timestamp", "device", "timestamp"),)


class TrainedModel(Base):
    __tablename__ = "trained_models"

    id: Mapped[int_pk]
    model_data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    trained_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    trained_by: Mapped[str] = mapped_column(default="user")
    points_count: Mapped[int]
    period_from: Mapped[datetime]
    period_to: Mapped[datetime]
    note: Mapped[str] = mapped_column(nullable=True)


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int_pk]
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="user")

    def set_password(self, password: str):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode(
            "utf-8"
        )

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )
