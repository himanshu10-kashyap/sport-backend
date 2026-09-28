from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from utils.common_schema import api_response_error, api_response_success
from utils.redis import CachedUpstreamError
from utils.status_code import StatusCode

from .cricket_external_api import (
    CricketExternalAPIError,
    cricket_external_api,
)


CricketRequest = Callable[..., Awaitable[Any]]


async def _fetch_cricket_data(
    request: CricketRequest,
    **kwargs: Any,
):
    try:
        data = await request(**kwargs)
        return api_response_success(data=data)
    except CachedUpstreamError as error:
        return api_response_error(
            error.message,
            error.status_code or StatusCode.internalServerError,
            None,
        )
    except CricketExternalAPIError as error:
        return api_response_error(error.message, error.status_code, None)
    except ValueError:
        return api_response_error(
            "Invalid cricket request", StatusCode.badRequest, None
        )
    except Exception:
        return api_response_error(
            "Unable to fetch cricket data", StatusCode.internalServerError, None
        )


async def get_cricket_events(
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.events,
        params=params,
    )


async def get_cricket_fixtures_today(
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.fixtures_today,
        params=params,
    )


async def get_cricket_event(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_ball_by_ball(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_ball_by_ball,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_best_players(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_best_players,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_enrichments(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_enrichments,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_enrichment(
    event_id: str,
    enrichment_type: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_enrichment,
        event_id=event_id,
        enrichment_type=enrichment_type,
        params=params,
    )


async def get_cricket_event_h2h(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_h2h,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_innings(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_innings,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_odds(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_odds,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_overs(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_overs,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_period_scores(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_period_scores,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_pregame_form(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_pregame_form,
        event_id=event_id,
        params=params,
    )


async def get_cricket_event_team_streaks(
    event_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.event_team_streaks,
        event_id=event_id,
        params=params,
    )


async def get_cricket_teams(
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.teams,
        params=params,
    )


async def get_cricket_team(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_enrichments(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_enrichments,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_enrichment(
    team_id: str,
    enrichment_type: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_enrichment,
        team_id=team_id,
        enrichment_type=enrichment_type,
        params=params,
    )


async def get_cricket_team_events(
    team_id: str,
    direction: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_events,
        team_id=team_id,
        direction=direction,
        params=params,
    )


async def get_cricket_team_featured_event(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_featured_event,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_media(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_media,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_near_events(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_near_events,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_performance(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_performance,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_players(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_players,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_rankings(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_rankings,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_standings_seasons(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_standings_seasons,
        team_id=team_id,
        params=params,
    )


async def get_cricket_team_unique_tournaments(
    team_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.team_unique_tournaments,
        team_id=team_id,
        params=params,
    )


async def get_cricket_manager(
    manager_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.manager,
        manager_id=manager_id,
        params=params,
    )


async def get_cricket_players(
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.players,
        params=params,
    )


async def get_cricket_player(
    player_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.player,
        player_id=player_id,
        params=params,
    )


async def get_cricket_player_events(
    player_id: str,
    direction: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.player_events,
        player_id=player_id,
        direction=direction,
        params=params,
    )


async def get_cricket_player_statistics(
    player_id: str,
    tournament_id: str,
    season_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.player_statistics,
        player_id=player_id,
        tournament_id=tournament_id,
        season_id=season_id,
        params=params,
    )


async def get_cricket_tournaments(
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.tournaments,
        params=params,
    )


async def get_cricket_tournament(
    tournament_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.tournament,
        tournament_id=tournament_id,
        params=params,
    )


async def get_cricket_tournament_events(
    tournament_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.tournament_events,
        tournament_id=tournament_id,
        params=params,
    )


async def get_cricket_tournament_scheduled_events(
    tournament_id: str,
    date: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.tournament_scheduled_events,
        tournament_id=tournament_id,
        date=date,
        params=params,
    )


async def get_cricket_tournament_standings(
    tournament_id: str,
    season_id: str,
    standings_type: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.tournament_standings,
        tournament_id=tournament_id,
        season_id=season_id,
        standings_type=standings_type,
        params=params,
    )


async def get_cricket_tournament_seasons(
    tournament_id: str,
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.tournament_seasons,
        tournament_id=tournament_id,
        params=params,
    )


async def search_cricket(
    params: Mapping[str, Any] | None = None,
):
    return await _fetch_cricket_data(
        cricket_external_api.search,
        params=params,
    )
