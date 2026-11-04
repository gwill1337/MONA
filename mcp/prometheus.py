import json
import os

import httpx2
from server import mcp

MONA_API_URL = os.getenv("MONA_API_URL", "http://api:30082")

@mcp.tool()
def get_prometheus_targets() -> str:
    """Get configured Prometheus scrape targets from MONA."""
    try:
        response = httpx2.get(
            f"{MONA_API_URL}/api/prometheus/targets",
            timeout=5.0,
        )
        response.raise_for_status()

        targets = response.json()

        return json.dumps({
            "status": "success",
            "count": len(targets),
            "targets": targets,
        }, ensure_ascii=False)

    except httpx2.HTTPError:
        return json.dumps({
            "status": "error",
            "message": "Unable to retrieve Prometheus targets from MONA API",
        }, ensure_ascii=False)
