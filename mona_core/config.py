from celery import Celery
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import from_url


class Settings(BaseSettings):
    # api
    cors_origins: list[str] = ["http://localhost:30081", "http://localhost:5173"]

    # Security
    max_attempts: int = 5
    lockout_seconds: int = 300
    session_ttl: int = 43200

    # ML
    window: int = 500
    min_points: int = 30
    contamination: float = 0.05
    score_threshold: float = -0.05

    # DB
    redis_url: str = "redis://redis:6379"

    # DON'T TOUCH!!!!
    database_url: str | None = None

    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""
    postgres_host: str = ""
    postgres_port: int = 5432

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

redis_url = settings.redis_url
redis_client = from_url(redis_url, decode_responses=True)
celery_client = Celery("mona", broker=redis_url, backend=redis_url)
