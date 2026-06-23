from celery import Celery
import os


app = Celery("mona")

app.conf.broker_url = os.getenv("REDIS_URL", "redis://redis:6379")

database_url = os.getenv("DATABASE_URL", "postgresql://myuser:1234@postgres:5432/mydb")
if not database_url.startswith("db+"):
    database_url = f"db+{database_url}"
app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", database_url)

app.conf.timezone = "UTC"

import py.tasks as tasks
import py.ml as ml

app.conf.worker_pool = 'solo'

app.conf.beat_schedule = {
    "collect" : {
        "task" : "tasks.collect_and_save",
        "schedule": 5,
    },

    "detect" : {
        "task" : "ml.detect_anomalies",
        "schedule": 60,
    },
}