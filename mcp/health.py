import json
import os

import httpx2
from server import mcp

MONA_API_URL = os.getenv(
    "MONA_API_URL",
    "http://api:8000",
)

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus:9090",
)

@mcp.tool()
def get_mona_health() -> str:
    """Check the availability of MONA API and Prometheus."""
    services = {
        "postgres": f"{MONA_API_URL}/health/live",
        "redis": f"{MONA_API_URL}/health/ready",
        "prometheus": f"{PROMETHEUS_URL}/-/healthy",
    }

    results = {}

    for name, url in services.items():
        try:
            response = httpx2.get(url, timeout=3.0)
            results[name] = {
                "status": "healthy" if response.is_success else "unhealthy",
                "http_status": response.status_code,
            }
        except httpx2.HTTPError:
            results[name] = {
                "status": "unreachable",
            }

    overall = (
        "healthy"
        if all(item["status"] == "healthy" for item in results.values())
        else "degraded"
    )

    return json.dumps({
        "status": overall,
        "services": results,
    }, ensure_ascii=False)
