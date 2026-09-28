import asyncio
import hashlib
import os
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import quote

import httpx

from utils.rate_limit import get_rate_limit_seconds
from utils.redis import acquire_rate_limit_slot, get_or_set_cached


def _env_float(name: str, fallback: float) -> float:
    try:
        return float(os.getenv(name, str(fallback)))
    except (TypeError, ValueError):
        return fallback


def _env_bool(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class CricketExternalAPIError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SportsAPI365Client:
    retry_status_codes = frozenset({429, 500, 502, 503, 504})

    live_cache_paths = frozenset(
        {
            "/event/{event_id}",
            "/event/{event_id}/ball-by-ball",
            "/event/{event_id}/innings",
            "/event/{event_id}/odds",
            "/event/{event_id}/overs",
            "/event/{event_id}/period-scores",
        }
    )

    default_cache_paths = frozenset(
        {
            "/events",
            "/fixtures/today",
            "/event/{event_id}",
        }
    )

    short_cache_paths = frozenset(
        {
            "/search",
            "/team/{team_id}/events/{direction}",
            "/team/{team_id}/near-events",
            "/team/{team_id}/featured-event",
            "/player/{player_id}/events/{direction}",
            "/unique-tournament/{tournament_id}/events",
            "/unique-tournament/{tournament_id}/scheduled-events/{date}",
        }
    )

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        rate_limit_seconds: float | None = None,
        rate_limit_getter: Callable[[], Awaitable[int | float]] | None = None,
        client: httpx.AsyncClient | None = None,
        redis_rate_limit_key: str | None = None,
    ):
        self.base_url = (
            base_url or os.getenv("SPORTS_API_BASE_URL", "")
        ).strip().rstrip("/")
        self.api_key = (
            api_key
            if api_key is not None
            else os.getenv("SPORTS_API_KEY", "")
        )
        self.timeout = (
            timeout
            if timeout is not None
            else float(os.getenv("SPORTS_API_TIMEOUT_SECONDS", "10"))
        )
        self.max_retries = max(
            0,
            max_retries
            if max_retries is not None
            else int(os.getenv("SPORTS_API_MAX_RETRIES", "2")),
        )
        self.rate_limit_seconds = max(
            0.0,
            rate_limit_seconds
            if rate_limit_seconds is not None
            else float(os.getenv("API_RATE_LIMIT_SECONDS", "2")),
        )
        self.rate_limit_getter = rate_limit_getter
        if self.rate_limit_getter is None and rate_limit_seconds is None:
            self.rate_limit_getter = get_rate_limit_seconds
        self.client = client
        self.redis_rate_limit_key = (
            redis_rate_limit_key
            if redis_rate_limit_key is not None
            else os.getenv("REDIS_RATE_LIMIT_KEY", "")
        ).strip() or "rl:sportsapi365"
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

        self.cache_enabled = _env_bool("EXTERNAL_API_CACHE_ENABLED", True)
        self.cache_prefix = os.getenv(
            "EXTERNAL_API_CACHE_PREFIX", "ext:sportsapi365"
        ).strip().rstrip(":")
        self.live_cache_ttl = max(
            0.0, _env_float("EXTERNAL_API_LIVE_CACHE_SECONDS", 2)
        )
        self.default_cache_ttl = max(
            0.0, _env_float("EXTERNAL_API_DEFAULT_CACHE_SECONDS", 2)
        )
        self.short_cache_ttl = max(
            0.0, _env_float("EXTERNAL_API_SHORT_CACHE_SECONDS", 30)
        )
        self.static_cache_ttl = max(
            0.0, _env_float("EXTERNAL_API_STATIC_CACHE_SECONDS", 300)
        )
        self.request_budget_seconds = (
            (self.max_retries + 1) * self.timeout
            + sum(min(0.25 * (2**attempt), 4.0) for attempt in range(self.max_retries))
        )
        self.cache_lock_ttl = max(
            1.0,
            _env_float(
                "EXTERNAL_API_CACHE_LOCK_SECONDS", self.request_budget_seconds + 5
            ),
        )
        self.cache_wait_seconds = max(
            0.0,
            _env_float(
                "EXTERNAL_API_CACHE_WAIT_SECONDS", self.request_budget_seconds + 5
            ),
        )
        self.cache_poll_interval = max(
            0.01, _env_float("EXTERNAL_API_CACHE_POLL_SECONDS", 0.05)
        )
        self.cache_poll_backoff = max(
            1.0, _env_float("EXTERNAL_API_CACHE_POLL_BACKOFF", 2.0)
        )
        self.cache_poll_max_interval = max(
            self.cache_poll_interval,
            _env_float("EXTERNAL_API_CACHE_POLL_MAX_SECONDS", 0.5),
        )
        self.cache_error_ttl = max(
            0.0, _env_float("EXTERNAL_API_CACHE_ERROR_SECONDS", 2)
        )
        self.case_insensitive_params = frozenset(
            name.strip().lower()
            for name in os.getenv(
                "EXTERNAL_API_CACHE_CI_PARAMS",
                "q,search,query,keyword,name,type,series_id,tournament_id,season_id",
            ).split(",")
            if name.strip()
        )

    def _resolve_cache_ttl(self, path: str) -> float:
        if not self.cache_enabled:
            return 0.0
        if path in self.default_cache_paths:
            return self.default_cache_ttl
        if path in self.live_cache_paths:
            return self.live_cache_ttl
        if path in self.short_cache_paths:
            return self.short_cache_ttl
        return self.static_cache_ttl

    def _build_cache_key(
        self,
        path: str,
        params: Mapping[str, Any] | None,
    ) -> str:
        cleaned = self._clean_params(params) or {}
        normalized = []
        for key in sorted(cleaned, key=str):
            value = cleaned[key]
            if str(key).lower() in self.case_insensitive_params:
                value = str(value).strip().lower()
            normalized.append(f"{key}={value}")

        canonical = path
        if normalized:
            canonical = f"{path}?{'&'.join(normalized)}"

        digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
        return f"{self.cache_prefix}:{digest}"

    @staticmethod
    def _build_path(path: str, path_params: Mapping[str, Any]) -> str:
        path_parts = path.strip("/").split("/")
        built_parts = []
        used_params = set()

        for path_part in path_parts:
            if path_part.startswith("{") and path_part.endswith("}"):
                parameter_name = path_part[1:-1]
                if parameter_name not in path_params:
                    raise ValueError(f"Missing path parameter: {parameter_name}")
                value = path_params[parameter_name]
                if value is None or not str(value).strip():
                    raise ValueError(f"Invalid path parameter: {parameter_name}")
                built_parts.append(quote(str(value), safe=""))
                used_params.add(parameter_name)
            else:
                built_parts.append(path_part)

        unused_params = set(path_params) - used_params
        if unused_params:
            names = ", ".join(sorted(unused_params))
            raise ValueError(f"Unexpected path parameters: {names}")

        return "/".join(built_parts)

    @staticmethod
    def _clean_params(
        params: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not params:
            return None
        return {
            str(key): value
            for key, value in params.items()
            if value is not None and str(value) != ""
        }

    async def _get_rate_limit_seconds(self) -> float:
        if self.rate_limit_getter is None:
            return self.rate_limit_seconds

        try:
            value = await self.rate_limit_getter()
            return max(0.0, float(value))
        except Exception:
            return self.rate_limit_seconds

    async def _wait_for_rate_limit(self) -> None:
        rate_limit_seconds = await self._get_rate_limit_seconds()
        if rate_limit_seconds <= 0:
            return

        if self.redis_rate_limit_key:
            acquired = await acquire_rate_limit_slot(
                self.redis_rate_limit_key,
                rate_limit_seconds,
            )
            if acquired:
                async with self._request_lock:
                    self._last_request_at = time.monotonic()
                return

        async with self._request_lock:
            elapsed = time.monotonic() - self._last_request_at
            wait_time = rate_limit_seconds - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request_at = time.monotonic()

    @staticmethod
    def _retry_delay(attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), 10.0)
            except ValueError:
                pass
        return min(0.25 * (2**attempt), 4.0)

    @staticmethod
    def _response_error(
        response: httpx.Response,
    ) -> CricketExternalAPIError:
        if response.status_code == 429:
            return CricketExternalAPIError(
                "SportsAPI365 rate limit exceeded", 429
            )
        if response.status_code in {401, 403}:
            return CricketExternalAPIError(
                "SportsAPI365 authentication failed", 502
            )
        if response.status_code == 404:
            return CricketExternalAPIError("Cricket resource not found", 404)
        if 400 <= response.status_code < 500:
            return CricketExternalAPIError(
                "SportsAPI365 rejected the cricket request", 400
            )
        return CricketExternalAPIError(
            "SportsAPI365 service is temporarily unavailable", 502
        )

    @staticmethod
    def _parse_response(response: httpx.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise CricketExternalAPIError(
                "SportsAPI365 returned invalid JSON", 502
            ) from error

    async def _fetch(
        self,
        url: str,
        query_params: Mapping[str, Any] | None,
        headers: Mapping[str, str],
    ) -> Any:
        for attempt in range(self.max_retries + 1):
            await self._wait_for_rate_limit()
            try:
                if self.client is not None:
                    response = await self.client.get(
                        url,
                        headers=dict(headers),
                        params=query_params,
                        timeout=self.timeout,
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(
                            url,
                            headers=dict(headers),
                            params=query_params,
                        )
            except httpx.RequestError as error:
                if attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(attempt, None))
                    continue
                raise CricketExternalAPIError(
                    "Unable to reach SportsAPI365", 502
                ) from error

            if response.status_code in self.retry_status_codes:
                if attempt < self.max_retries:
                    await asyncio.sleep(
                        self._retry_delay(
                            attempt,
                            response.headers.get("Retry-After"),
                        )
                    )
                    continue
                raise self._response_error(response)

            if response.status_code >= 300:
                raise self._response_error(response)

            return self._parse_response(response)

        raise CricketExternalAPIError(
            "Unable to reach SportsAPI365", 502
        )

    async def _request(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        **path_params: Any,
    ) -> Any:
        if not self.base_url:
            raise CricketExternalAPIError(
                "SPORTS_API_BASE_URL is not configured", 500
            )
        if not self.api_key:
            raise CricketExternalAPIError(
                "SportsAPI365 API key is not configured", 500
            )

        url = f"{self.base_url}/{self._build_path(path, path_params)}"
        query_params = self._clean_params(params)
        headers = {
            "Accept": "application/json",
            "X-Gravitee-Api-Key": self.api_key,
        }

        cache_ttl = self._resolve_cache_ttl(path)
        if cache_ttl <= 0:
            return await self._fetch(url, query_params, headers)

        return await get_or_set_cached(
            key=self._build_cache_key(path, query_params),
            ttl=cache_ttl,
            lock_ttl=self.cache_lock_ttl,
            wait_seconds=self.cache_wait_seconds,
            poll_interval=self.cache_poll_interval,
            poll_backoff=self.cache_poll_backoff,
            poll_max_interval=self.cache_poll_max_interval,
            error_ttl=self.cache_error_ttl,
            loader=lambda: self._fetch(url, query_params, headers),
        )

    async def events(
        self, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request("/events", params=params)

    async def fixtures_today(
        self, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request("/fixtures/today", params=params)

    async def event(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}", params=params, event_id=event_id
        )

    async def event_ball_by_ball(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/ball-by-ball",
            params=params,
            event_id=event_id,
        )

    async def event_best_players(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/best-players",
            params=params,
            event_id=event_id,
        )

    async def event_enrichments(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/enrichments",
            params=params,
            event_id=event_id,
        )

    async def event_enrichment(
        self,
        event_id: str,
        enrichment_type: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/event/{event_id}/enrichments/{enrichment_type}",
            params=params,
            event_id=event_id,
            enrichment_type=enrichment_type,
        )

    async def event_h2h(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/h2h",
            params=params,
            event_id=event_id,
        )

    async def event_innings(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/innings",
            params=params,
            event_id=event_id,
        )

    async def event_odds(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/odds",
            params=params,
            event_id=event_id,
        )

    async def event_overs(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/overs",
            params=params,
            event_id=event_id,
        )

    async def event_period_scores(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/period-scores",
            params=params,
            event_id=event_id,
        )

    async def event_pregame_form(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/pregame-form",
            params=params,
            event_id=event_id,
        )

    async def event_team_streaks(
        self, event_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/event/{event_id}/team-streaks",
            params=params,
            event_id=event_id,
        )

    async def teams(
        self, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request("/teams", params=params)

    async def team(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}", params=params, team_id=team_id
        )

    async def team_enrichments(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/enrichments",
            params=params,
            team_id=team_id,
        )

    async def team_enrichment(
        self,
        team_id: str,
        enrichment_type: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/team/{team_id}/enrichments/{enrichment_type}",
            params=params,
            team_id=team_id,
            enrichment_type=enrichment_type,
        )

    async def team_events(
        self,
        team_id: str,
        direction: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/team/{team_id}/events/{direction}",
            params=params,
            team_id=team_id,
            direction=direction,
        )

    async def team_featured_event(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/featured-event",
            params=params,
            team_id=team_id,
        )

    async def team_media(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/media",
            params=params,
            team_id=team_id,
        )

    async def team_near_events(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/near-events",
            params=params,
            team_id=team_id,
        )

    async def team_performance(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/performance",
            params=params,
            team_id=team_id,
        )

    async def team_players(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/players",
            params=params,
            team_id=team_id,
        )

    async def team_rankings(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/rankings",
            params=params,
            team_id=team_id,
        )

    async def team_standings_seasons(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/standings-seasons",
            params=params,
            team_id=team_id,
        )

    async def team_unique_tournaments(
        self, team_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/team/{team_id}/unique-tournaments",
            params=params,
            team_id=team_id,
        )

    async def manager(
        self, manager_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/manager/{manager_id}",
            params=params,
            manager_id=manager_id,
        )

    async def players(
        self, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request("/players", params=params)

    async def player(
        self, player_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/player/{player_id}", params=params, player_id=player_id
        )

    async def player_events(
        self,
        player_id: str,
        direction: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/player/{player_id}/events/{direction}",
            params=params,
            player_id=player_id,
            direction=direction,
        )

    async def player_statistics(
        self,
        player_id: str,
        tournament_id: str,
        season_id: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/statistics",
            params=params,
            player_id=player_id,
            tournament_id=tournament_id,
            season_id=season_id,
        )

    async def tournaments(
        self, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request("/tournaments", params=params)

    async def tournament(
        self, tournament_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/unique-tournament/{tournament_id}",
            params=params,
            tournament_id=tournament_id,
        )

    async def tournament_events(
        self, tournament_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/unique-tournament/{tournament_id}/events",
            params=params,
            tournament_id=tournament_id,
        )

    async def tournament_scheduled_events(
        self,
        tournament_id: str,
        date: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/unique-tournament/{tournament_id}/scheduled-events/{date}",
            params=params,
            tournament_id=tournament_id,
            date=date,
        )

    async def tournament_standings(
        self,
        tournament_id: str,
        season_id: str,
        standings_type: str,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._request(
            "/unique-tournament/{tournament_id}/season/{season_id}/standings/{standings_type}",
            params=params,
            tournament_id=tournament_id,
            season_id=season_id,
            standings_type=standings_type,
        )

    async def tournament_seasons(
        self, tournament_id: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request(
            "/unique-tournament/{tournament_id}/seasons",
            params=params,
            tournament_id=tournament_id,
        )

    async def search(
        self, params: Mapping[str, Any] | None = None
    ) -> Any:
        return await self._request("/search", params=params)


cricket_external_api = SportsAPI365Client()
