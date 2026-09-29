import asyncio
import os
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.database import AsyncSessionLocal
from src.models.rate_limit_model import RATE_LIMIT_DEFAULT_SECONDS, RateLimit
from utils.redis import (
    UpstreamRateLimitUnavailable,
    retry_after_seconds,
    try_acquire_rate_limit_slot,
)


RATE_LIMIT_CACHE_TTL_SECONDS = 5.0
_FALLBACK_PRUNE_THRESHOLD = 10_000

_rate_limit_cache: tuple[float, int] | None = None


def _env_bool(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}


async def get_rate_limit_seconds() -> int:
    global _rate_limit_cache

    cached = _rate_limit_cache
    if cached is not None:
        if time.monotonic() - cached[0] < RATE_LIMIT_CACHE_TTL_SECONDS:
            return cached[1]

    try:
        async with AsyncSessionLocal() as db:
            value = (
                await db.execute(
                    select(RateLimit.value).where(RateLimit.id == 1)
                )
            ).scalars().first()
    except Exception:
        return cached[1] if cached is not None else RATE_LIMIT_DEFAULT_SECONDS

    seconds = RATE_LIMIT_DEFAULT_SECONDS if value is None else max(1, int(value))
    _rate_limit_cache = (time.monotonic(), seconds)
    return seconds


def invalidate_rate_limit_cache() -> None:
    global _rate_limit_cache
    _rate_limit_cache = None


def _env_prefixes(name: str, fallback: str) -> tuple[str, ...]:
    raw = os.getenv(name, fallback)
    return tuple(
        item.strip().rstrip("/")
        for item in raw.split(",")
        if item.strip()
    )


class DynamicRateLimitMiddleware(BaseHTTPMiddleware):
    # Per-IP user limiter. Deliberately off.
    #
    # It runs before the route handler, so it rejects a user before Redis is
    # ever consulted - and every cricket response is a cheap cache read
    # (stale data is served while a refresh runs in the background). The
    # only effect of turning this on is 429ing requests that the cache
    # would have answered in ~80ms. Provider pressure is handled by the
    # outbound limiter in the cricket client, which is driven by the
    # admin-set value.
    ENABLED = False

    def __init__(
        self,
        app,
        key_prefix: str | None = None,
        trust_proxy_headers: bool | None = None,
        limited_paths: tuple[str, ...] | None = None,
        excluded_paths: tuple[str, ...] | None = None,
    ):
        super().__init__(app)
        self.enabled = self.ENABLED
        # Flip USER_RATE_LIMIT_TRUST_PROXY to 1 when deploying behind a load
        # balancer, ALB or Cloudflare. Without it every request resolves to the
        # proxy's IP, so all users share one bucket and the first one to be
        # limited blocks everyone else. Do NOT enable it without a trusted
        # proxy rewriting the header - anyone can spoof X-Forwarded-For and
        # dodge the limit otherwise.
        self.trust_proxy_headers = (
            _env_bool("USER_RATE_LIMIT_TRUST_PROXY", False)
            if trust_proxy_headers is None
            else trust_proxy_headers
        )
        self.key_prefix = (
            key_prefix
            if key_prefix is not None
            else os.getenv("USER_RATE_LIMIT_KEY_PREFIX", "rl:user:")
        ).strip()
        self.limited_paths = (
            limited_paths
            if limited_paths is not None
            else _env_prefixes("USER_RATE_LIMIT_PATHS", "/api/v1/cricket")
        )
        self.excluded_paths = (
            excluded_paths
            if excluded_paths is not None
            else _env_prefixes("USER_RATE_LIMIT_EXCLUDE_PATHS", "/api/admin")
        )
        self._fallback_hits: dict[str, float] = {}
        self._fallback_lock = asyncio.Lock()

    def _prune_fallback(self, interval: float) -> None:
        if len(self._fallback_hits) < _FALLBACK_PRUNE_THRESHOLD:
            return
        cutoff = time.monotonic() - max(interval, 1.0)
        for key in [k for k, v in self._fallback_hits.items() if v < cutoff]:
            self._fallback_hits.pop(key, None)

    async def _fallback_acquire(self, identity: str, interval: float) -> bool:
        async with self._fallback_lock:
            self._prune_fallback(interval)
            now = time.monotonic()
            previous = self._fallback_hits.get(identity, 0.0)
            if now - previous < interval:
                return False
            self._fallback_hits[identity] = now
            return True

    def _client_identity(self, request: Request) -> str:
        if self.trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                first = forwarded.split(",")[0].strip()
                if first:
                    return first
            real_ip = request.headers.get("x-real-ip")
            if real_ip and real_ip.strip():
                return real_ip.strip()

        client = request.client
        return client.host if client else "unknown"

    def _is_limited(self, path: str) -> bool:
        normalized = path.rstrip("/")
        for excluded in self.excluded_paths:
            if normalized == excluded or normalized.startswith(f"{excluded}/"):
                return False
        for prefix in self.limited_paths:
            if normalized == prefix or normalized.startswith(f"{prefix}/"):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        if not self._is_limited(request.url.path):
            return await call_next(request)

        interval = float(await get_rate_limit_seconds())
        if interval <= 0:
            return await call_next(request)

        client_ip = self._client_identity(request)
        key = f"{self.key_prefix}{client_ip}"

        try:
            acquired = await try_acquire_rate_limit_slot(key, interval)
        except UpstreamRateLimitUnavailable:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "status_code": 503,
                    "message": "Rate limiter unavailable, please try again later",
                    "data": None,
                },
            )

        if acquired:
            return await call_next(request)

        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(
                    int((await retry_after_seconds(key, interval)) + 0.999)
                ),
            },
            content={
                "success": False,
                "status_code": 429,
                "message": "Too many requests, please try again later",
                "data": None,
            },
        )
