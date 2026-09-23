import time

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.database import AsyncSessionLocal
from src.models.rate_limit_model import RATE_LIMIT_DEFAULT_SECONDS, RateLimit


async def get_rate_limit_seconds() -> int:
    try:
        async with AsyncSessionLocal() as db:
            value = (
                await db.execute(
                    select(RateLimit.value).where(RateLimit.id == 1)
                )
            ).scalars().first()
        if value is None:
            return RATE_LIMIT_DEFAULT_SECONDS
        return max(1, int(value))
    except Exception:
        return RATE_LIMIT_DEFAULT_SECONDS


class DynamicRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.last_hits = {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path.startswith("/api/admin/"):
            return await call_next(request)

        interval = await get_rate_limit_seconds()
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        prev = self.last_hits.get(client_ip, 0)

        if now - prev < interval:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "status_code": 429,
                    "message": "Too many requests, please try again later",
                    "data": None,
                },
            )

        self.last_hits[client_ip] = now
        return await call_next(request)