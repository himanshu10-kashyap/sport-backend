import asyncio
import json
import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from dotenv import load_dotenv
from redis.asyncio import Redis


logger = logging.getLogger(__name__)


load_dotenv(".env")
if os.getenv("NODE_ENV") == "production":
    load_dotenv(".env.production")


_RATE_LIMIT_SCRIPT = """
local previous = tonumber(redis.call('GET', KEYS[1]) or '0')
local now = tonumber(ARGV[1])
local interval = tonumber(ARGV[2])
local elapsed = now - previous

if elapsed < interval then
    return math.ceil((interval - elapsed) * 1000)
end

redis.call('SET', KEYS[1], ARGV[1], 'EX', math.ceil(interval))
return 0
"""

_RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

_redis_client: Redis | None = None
_redis_lock = asyncio.Lock()
_redis_disabled_until = 0.0


def _redis_protocol() -> int:
    try:
        return int(os.getenv("REDIS_PROTOCOL", "2"))
    except (TypeError, ValueError):
        return 2


def _redis_max_connections() -> int:
    # 300, not the redis-py default of 100. The cache sits on the hot path
    # for every cricket request and each single-flight waiter checks out a
    # connection per poll, so bursts exhaust a small pool and every request
    # starts queueing behind it.
    try:
        return max(10, int(os.getenv("REDIS_MAX_CONNECTIONS", "300")))
    except (TypeError, ValueError):
        return 300


def _is_pool_exhausted(error: BaseException) -> bool:
    return type(error).__name__ == "MaxConnectionsError"


def _create_redis_client() -> Redis | None:
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0").strip()
    if not redis_url:
        return None
    try:
        return Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            health_check_interval=30,
            protocol=_redis_protocol(),
            max_connections=_redis_max_connections(),
        )
    except Exception:
        return None


def _disable_redis() -> None:
    global _redis_disabled_until
    _redis_disabled_until = time.monotonic() + 30


async def _get_available_redis_client() -> Redis | None:
    global _redis_client

    if time.monotonic() < _redis_disabled_until:
        return None

    async with _redis_lock:
        if time.monotonic() < _redis_disabled_until:
            return None

        if _redis_client is None:
            _redis_client = _create_redis_client()

        if _redis_client is None:
            _disable_redis()
            return None

        try:
            await _redis_client.ping()
        except Exception as error:
            if _is_pool_exhausted(error):
                return _redis_client
            _disable_redis()
            try:
                await _redis_client.aclose()
            except Exception:
                pass
            _redis_client = None
            return None

        return _redis_client


async def get_redis_client() -> Redis | None:
    return await _get_available_redis_client()


async def redis_is_available() -> bool:
    return await _get_available_redis_client() is not None


async def close_redis_client() -> None:
    global _redis_client

    async with _redis_lock:
        client = _redis_client
        _redis_client = None
        if client is None:
            return
        try:
            await client.aclose()
        except Exception:
            pass


async def acquire_rate_limit_slot(
    key: str,
    interval: float,
    max_wait: float | None = None,
) -> bool | None:
    """Try to take the slot.

    True  - slot taken, go ahead
    False - Redis is healthy but the slot stayed busy for the whole budget
    None  - Redis is unavailable, caller may fall back to a local throttle
    """
    if interval <= 0:
        return True

    client = await _get_available_redis_client()
    if client is None:
        return None

    # Without max_wait the caller accepts the full interval. Callers that
    # must not block a user request pass max_wait to give up early and let
    # them serve stale data instead.
    budget = (
        max(1.0, float(interval) + 1.0)
        if max_wait is None
        else max(0.0, float(max_wait))
    )
    deadline = time.monotonic() + budget
    while time.monotonic() < deadline:
        try:
            wait_milliseconds = int(
                await client.eval(
                    _RATE_LIMIT_SCRIPT,
                    1,
                    key,
                    str(time.time()),
                    str(interval),
                )
                or 0
            )
        except Exception as error:
            if not _is_pool_exhausted(error):
                _disable_redis()
            return None

        if wait_milliseconds <= 0:
            return True

        await asyncio.sleep(min(wait_milliseconds / 1000, 1.0))

    return False


async def try_acquire_rate_limit_slot(
    key: str,
    interval: float,
) -> bool | None:
    if interval <= 0:
        return True

    client = await _get_available_redis_client()
    if client is None:
        return None

    try:
        wait_milliseconds = int(
            await client.eval(
                _RATE_LIMIT_SCRIPT,
                1,
                key,
                str(time.time()),
                str(interval),
            )
            or 0
        )
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()
        return None

    return wait_milliseconds <= 0


async def retry_after_seconds(key: str, interval: float) -> float:
    client = await _get_available_redis_client()
    if client is None:
        return float(interval)

    try:
        last = await client.get(key)
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()
        return float(interval)

    if not last:
        return 0.0

    try:
        remaining = float(interval) - (time.time() - float(last))
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(remaining, float(interval)))


async def cache_get(key: str) -> Any:
    client = await _get_available_redis_client()
    if client is None:
        return None

    try:
        raw = await client.get(key)
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()
        return None

    if not raw:
        return None

    try:
        return json.loads(raw)
    except ValueError:
        return None


async def cache_set(key: str, value: Any, ttl: float) -> bool:
    if ttl <= 0:
        return False

    client = await _get_available_redis_client()
    if client is None:
        return False

    try:
        payload = json.dumps(value, separators=(",", ":"))
    except (TypeError, ValueError):
        return False

    try:
        await client.set(
            key,
            payload,
            ex=max(1, int(round(ttl))),
        )
        return True
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()
        return False


async def _acquire_cache_lock(key: str, ttl: float, token: str) -> bool:
    client = await _get_available_redis_client()
    if client is None:
        return True

    try:
        acquired = await client.set(
            key,
            token,
            nx=True,
            ex=max(1, int(round(ttl))),
        )
        return bool(acquired)
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()
        return True


async def _release_cache_lock(key: str, token: str) -> None:
    client = await _get_available_redis_client()
    if client is None:
        return

    try:
        await client.eval(_RELEASE_LOCK_SCRIPT, 1, key, token)
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()


_CACHE_ERROR_MARKER = "__cached_error__"
_SWR_MARKER = "__swr__"


def _swr_envelope(value: Any, fresh: float) -> dict:
    return {
        _SWR_MARKER: {"at": time.time(), "fresh": float(fresh)},
        "data": value,
    }


def _read_swr_envelope(cached: Any) -> tuple[Any, float, float] | None:
    """Return (value, fresh_seconds, age_seconds) for an enveloped entry.

    Anything that is not an envelope (legacy plain values, error payloads)
    returns None so the caller can fall back to treating it as a hit.
    """
    if not isinstance(cached, dict):
        return None
    meta = cached.get(_SWR_MARKER)
    if not isinstance(meta, dict):
        return None
    if _CACHE_ERROR_MARKER in cached:
        return None
    try:
        fresh = float(meta.get("fresh", 0.0))
        age = max(0.0, time.time() - float(meta.get("at", 0.0)))
    except (TypeError, ValueError):
        return None
    return cached.get("data"), fresh, age


async def cache_get_swr(key: str) -> tuple[str, Any]:
    """Return (state, value) where state is one of:

    "fresh"  - younger than its own fresh window
    "stale"  - past fresh, still inside the stale window
    "plain"  - a legacy/non-enveloped entry, treat as a normal hit
    "error"  - a cached upstream failure
    "miss"   - nothing stored
    """
    cached = await cache_get(key)
    if cached is None:
        return "miss", None

    if isinstance(cached, dict) and _CACHE_ERROR_MARKER in cached:
        return "error", cached

    parsed = _read_swr_envelope(cached)
    if parsed is None:
        return "plain", cached

    value, fresh, age = parsed
    return ("fresh" if age < fresh else "stale"), value


async def cache_set_swr(
    key: str,
    value: Any,
    fresh: float,
    stale: float,
) -> bool:
    """Store value so it is served as fresh for `fresh` seconds and as
    stale-but-usable for a further `stale` seconds."""
    hard_ttl = max(0.0, float(fresh)) + max(0.0, float(stale))
    if hard_ttl <= 0:
        return False

    client = await _get_available_redis_client()
    if client is None:
        return False

    try:
        payload = json.dumps(
            _swr_envelope(value, fresh), separators=(",", ":")
        )
    except (TypeError, ValueError):
        return False

    try:
        await client.set(key, payload, ex=max(1, int(round(hard_ttl))))
        return True
    except Exception as error:
        if not _is_pool_exhausted(error):
            _disable_redis()
        return False


class CachedUpstreamError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        original_type: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.original_type = original_type


def _error_payload(error: Exception) -> dict:
    return {
        _CACHE_ERROR_MARKER: {
            "type": type(error).__name__,
            "message": str(error),
            "status_code": getattr(error, "status_code", None),
        }
    }


def _is_transient_error(error: Exception) -> bool:
    """A rate-limit rejection is momentary, unlike a genuine upstream
    failure. Caching it would hand the same 429 to every reader for the
    whole error TTL and cascade one busy slot into a burst of failures."""
    return getattr(error, "status_code", None) == 429


def raise_if_cached_error(cached: Any) -> None:
    if not isinstance(cached, dict):
        return
    failure = cached.get(_CACHE_ERROR_MARKER)
    if isinstance(failure, dict):
        raise CachedUpstreamError(
            str(failure.get("message") or "upstream error"),
            failure.get("status_code"),
            failure.get("type"),
        )


async def get_or_set_cached(
    key: str,
    ttl: float,
    lock_ttl: float,
    wait_seconds: float,
    poll_interval: float,
    poll_backoff: float,
    poll_max_interval: float,
    error_ttl: float,
    loader: Callable[[], Awaitable[Any]],
    stale: float = 0.0,
) -> Any:
    if ttl <= 0 and stale <= 0:
        return await loader()

    async def _read() -> Any:
        if stale > 0:
            state, value = await cache_get_swr(key)
            if state == "miss":
                return None
            raise_if_cached_error(value)
            return value
        cached = await cache_get(key)
        if cached is not None:
            raise_if_cached_error(cached)
        return cached

    async def _write(value: Any) -> None:
        if stale > 0:
            await cache_set_swr(key, value, ttl, stale)
        else:
            await cache_set(key, value, ttl)

    cached = await _read()
    if cached is not None:
        return cached

    lock_key = f"{key}:lock"
    token = uuid.uuid4().hex

    if await _acquire_cache_lock(lock_key, lock_ttl, token):
        try:
            cached = await _read()
            if cached is not None:
                return cached
            try:
                value = await loader()
            except Exception as error:
                if error_ttl > 0 and not _is_transient_error(error):
                    await cache_set(key, _error_payload(error), error_ttl)
                raise
            await _write(value)
            return value
        finally:
            await _release_cache_lock(lock_key, token)

    deadline = time.monotonic() + max(0.0, wait_seconds)
    interval = max(0.005, poll_interval)
    ceiling = max(interval, poll_max_interval)

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(interval, remaining))
        cached = await _read()
        if cached is not None:
            return cached
        interval = min(ceiling, interval * poll_backoff)

    return await loader()


async def refresh_cached_swr(
    key: str,
    lock_ttl: float,
    fresh: float,
    stale: float,
    loader: Callable[[], Awaitable[Any]],
) -> bool:
    """Single-flight background refresh.

    Returns True when the value was refetched and re-stored, False when the
    lock was already held by another worker. Never raises: a failed refresh
    just leaves the previous (stale) entry in place for the next reader.
    """
    lock_key = f"{key}:lock"
    token = uuid.uuid4().hex

    if not await _acquire_cache_lock(lock_key, lock_ttl, token):
        return False

    try:
        value = await loader()
        await cache_set_swr(key, value, fresh, stale)
        return True
    except Exception:
        # The reader already has the previous snapshot, so this is not worth
        # failing their request over - but it must not vanish silently.
        logger.exception("background refresh failed for %s", key)
        return False
    finally:
        await _release_cache_lock(lock_key, token)
