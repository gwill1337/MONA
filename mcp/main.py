import devices  # noqa: F401 E402
import health  # noqa: F401 E402
import metrics  # noqa: F401 E402
import ml  # noqa: F401 E402
import prompts  # noqa: F401 E402
import resources  # noqa: F401 E402
from auth import ApiKeyAuthMiddleware
from starlette.middleware import Middleware
from server import mcp

import prometheus  # noqa: F401 E402

app = mcp.http_app(transport="sse", middleware=[Middleware(ApiKeyAuthMiddleware)])

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000) # noqa: S104
