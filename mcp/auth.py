import hashlib

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from mona_core.db import ApiKey, SessionLocal


def _is_valid(token: str) -> bool:
    key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with SessionLocal() as session:
        return session.query(ApiKey).filter_by(key_hash=key_hash).first() is not None


class ApiKeyAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        auth = headers.get("authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""

        if not token or not await run_in_threadpool(_is_valid, token):
            response = JSONResponse({"error": "Missing or invalid API key"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)