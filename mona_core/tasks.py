import os

import requests

from celery_conf import app
from db import Device, Metric, SessionLocal

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-main-metrics.mona.svc:9090",
)

def _query(prometheus_url: str, query: str) -> float:
    resp = requests.get(
        f"{prometheus_url}/api/v1/query",
        params={"query": query},
        timeout=5,
    )
    data = resp.json()
    return (
        float(data["data"]["result"][0]["value"][1])
        if data["data"]["result"]
        else 0
    )


@app.task(name="tasks.collect_and_save")
def collect_and_save():
    """CPU/RAM metrics from physical PCs via custom Prometheus."""
    db = SessionLocal()
    try:
        config_devices = os.getenv("EXPORTERS", "").split(",")

        for entry in config_devices:
            if not entry or ":" not in entry:
                continue

            device_name, device_ip = entry.split(":", 1)
            existing = db.query(Device).filter(Device.name == device_name).first()
            if not existing:
                new_dev = Device(name=device_name, ip=device_ip, is_active=True)
                db.add(new_dev)
            elif existing.ip != device_ip:
                existing.ip = device_ip

        db.commit()

        active_devices = db.query(Device).filter(Device.is_active).all()

        results = []
        for dev in active_devices:
            job = dev.name
            sel = f'job="{job}",physical_pc="true"'
            cpu_query = (
                f'100 * (1 - avg(rate(node_cpu_seconds_total{{{sel},mode="idle"}}[5m])))'
            )
            ram_query = (
                f'avg((1 - (node_memory_MemAvailable_bytes{{{sel}}}'
                f' / node_memory_MemTotal_bytes{{{sel}}})) * 100)'
            )
            cpu = _query(PROMETHEUS_URL, cpu_query)
            ram = _query(PROMETHEUS_URL, ram_query)

            metric = Metric(cpu=cpu, ram=ram, device=job)
            db.add(metric)
            results.append({"device": job, "cpu": round(cpu, 2), "ram": round(ram, 2)})

        db.commit()
        return results
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        return {"error": str(e)}
    finally:
        db.close()
