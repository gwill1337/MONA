import hashlib

from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from mona_core.db import ApiKey, SessionLocal


class ApiKeyAuthMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        headers = get_http_headers()

        if headers:
            auth_header = headers.get("authorization") or headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                raise PermissionError("Missing or invalid Authorization header")

            token = auth_header.split(" ")[1]
            incoming_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

            with SessionLocal() as session:
                db_key = session.query(ApiKey).filter_by(key_hash=incoming_hash).first()
                if not db_key:
                    raise PermissionError("Invalid API key")

        return await call_next(context)
