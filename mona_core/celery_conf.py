import os

from celery import Celery

from mona_core.config import settings

SCHEDULE_SECONDS = 30.0
TASK_EXPIRES_SECONDS = 60

app = Celery(
    "mona",
    include=["mona_core.tasks", "mona_core.ml"],
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    timezone="UTC",
    worker_pool="prefork",
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "2")),
    worker_prefetch_multiplier=1,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

app.conf.beat_schedule = {
    "collect": {
        "task": "tasks.collect_and_save",
        "schedule": SCHEDULE_SECONDS,
        "options": {"expires": TASK_EXPIRES_SECONDS},
    },
    "detect": {
        "task": "ml.detect_anomalies",
        "schedule": SCHEDULE_SECONDS,
        "options": {"expires": TASK_EXPIRES_SECONDS},
    },
}
