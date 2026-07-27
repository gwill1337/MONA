
from celery import Celery

from mona_core.config import settings

app = Celery("mona")

# redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
redis_url = settings.redis_url

app = Celery(
    "mona",
    include=["tasks", "ml"],
    broker=redis_url,
    backend=redis_url,
)


# database_url = os.getenv("DATABASE_URL", "postgresql://myuser:1234@postgres:5432/mydb")
database_url = settings.postgres_url
if not database_url.startswith("db+"):
    database_url = f"db+{database_url}"

app.conf.update(timezone="UTC", worker_pool="solo")

app.conf.beat_schedule = {
    "collect": {
        "task": "tasks.collect_and_save",
        "schedule": 30,
    },
    "detect": {
        "task": "ml.detect_anomalies",
        "schedule": 60,
    },
}
