from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):
    #api
    cors_origins: list[str] = ["http://localhost:30081"]

    #ML
    window: int = 500
    min_points: int = 30
    contamination: float = 0.05
    score_threshold: float = -0.05

    #DB
    redis_url: str = "redis://redis:6379"

    postgres_user: str = "myuser"
    postgres_password: str = ""
    postgres_db: str = "mydb"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @computed_field
    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()