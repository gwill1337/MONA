from celery import Celery

# app = Celery(
#     "tasks",
#     broker="redis://redis:6379",
#     backend="redis://redis:6379"
#              )

app = Celery("mona")

app.conf.broker_url = "redis://redis:6379"
app.conf.result_backend = "db+postgresql://myuser:1234@postgres:5432/mydb"

app.conf.timezone = "UTC"

import tasks
import ml

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