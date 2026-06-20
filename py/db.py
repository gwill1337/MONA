from sqlalchemy import create_engine, Column, Integer, Float, DateTime, Boolean, String, LargeBinary
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, UTC
import os

timestamp = datetime.now(UTC)

DATABASE = os.getenv("DATABASE_URL", "postgresql://myuser:1234@localhost:5432/mydb")


engine = create_engine(DATABASE)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True)
    cpu = Column(Float)
    ram = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))


class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(Integer, primary_key=True)
    metric_id = Column(Integer)
    cpu = Column(Float)
    ram = Column(Float)
    timestamp = Column(DateTime)
    reason = Column(String)
    score = Column(Float)
    detected_at = Column(DateTime, default=lambda: datetime.now(UTC))

class TrainedModel(Base):
    __tablename__ = "trained_models"
    id = Column(Integer, primary_key=True)
    model_data = Column(LargeBinary, nullable=False)
    trained_at = Column(DateTime, default=lambda: datetime.now(UTC))
    trained_by = Column(String, default="user")
    points_count = Column(Integer)
    period_from = Column(DateTime)
    period_to = Column(DateTime)
    note = Column(String, nullable=True)