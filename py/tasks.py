import os

import requests
from py.celery_conf import app
from py.db import SessionLocal, Metric

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-main-metrics.mona.svc:9090",
)
# Matches the job in the custom Prometheus ConfigMap (global.externalPcExporter.jobName).
PC_EXPORTER_JOB = os.getenv("PROMETHEUS_PC_JOB", "external-pc-node-exporter")


@app.task
def collect_and_save():
    """CPU/RAM metrics from a physical PC via custom Prometheus (physical_pc label)."""
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
        
        # Save to DB
        metric = Metric(cpu=cpu, ram=ram)
        db.add(metric)
        db.commit()
        
        return {"cpu": round(cpu, 2), "ram": round(ram, 2)}
        
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        return {"error": str(e)}
    finally:
        db.close()