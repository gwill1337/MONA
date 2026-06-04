
# import psutil
# from time import sleep

# from celery_conf import app
# from db import SessionLocal, Metric, Base, engine




# # @app.task
# # def collect_metrics():
# #     cpu = psutil.cpu_percent(interval=1)
# #     ram = psutil.virtual_memory().percent
# #     return cpu, ram
        

# # def save_metric(cpu, ram):
# #     db = SessionLocal()
# #     metric = Metric(cpu=cpu, ram=ram)
# #     db.add(metric)
# #     db.commit()
# #     db.close()

# # @app.task
# # def collect_and_save():
# #     cpu, ram = collect_metrics()
# #     save_metric(cpu, ram)

# @app.task  # ← ДЕКОРАТОР!
# def collect_and_save():
#     db = SessionLocal()
#     cpu = psutil.cpu_percent(interval=1)
#     ram = psutil.virtual_memory().percent
    
#     metric = Metric(cpu=cpu, ram=ram)
#     db.add(metric)
#     db.commit()
#     db.close()
    
#     return {"cpu": cpu, "ram": ram}


import os

import requests
from celery_conf import app
from db import SessionLocal, Metric

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-main-metrics.mona.svc:9090",
)
# Совпадает с job в ConfigMap кастомного Prometheus (global.externalPcExporter.jobName).
PC_EXPORTER_JOB = os.getenv("PROMETHEUS_PC_JOB", "external-pc-node-exporter")


@app.task
def collect_and_save():
    """Метрики CPU/RAM с физического ПК через кастомный Prometheus (лейбл physical_pc)."""
    db = SessionLocal()

    try:
        sel = f'job="{PC_EXPORTER_JOB}",physical_pc="true"'
        cpu_query = (
            f"100 * (1 - avg(rate(node_cpu_seconds_total{{{sel},mode=\"idle\"}}[5m])))"
        )
        cpu_response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": cpu_query},
            timeout=5,
        )
        cpu_data = cpu_response.json()
        cpu = (
            float(cpu_data["data"]["result"][0]["value"][1])
            if cpu_data["data"]["result"]
            else 0
        )

        ram_query = (
            "avg("
            f"(1 - (node_memory_MemAvailable_bytes{{{sel}}} "
            f"/ node_memory_MemTotal_bytes{{{sel}}})) * 100)"
        )
        ram_response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": ram_query},
            timeout=5
        )
        ram_data = ram_response.json()
        ram = float(ram_data['data']['result'][0]['value'][1]) if ram_data['data']['result'] else 0
        
        # Сохраните в БД
        metric = Metric(cpu=cpu, ram=ram)
        db.add(metric)
        db.commit()
        
        return {"cpu": round(cpu, 2), "ram": round(ram, 2)}
        
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        return {"error": str(e)}
    finally:
        db.close()