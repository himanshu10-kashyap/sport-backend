from fastapi import APIRouter, Depends, Path, Request

from .cricket_services import (
    get_cricket_event,
    get_cricket_event_ball_by_ball,
    get_cricket_event_best_players,
    get_cricket_event_enrichment,
    get_cricket_event_enrichments,
    get_cricket_event_h2h,
    get_cricket_event_innings,
    get_cricket_event_odds,
    get_cricket_event_overs,
    get_cricket_event_period_scores,
    get_cricket_event_pregame_form,
    get_cricket_event_team_streaks,
    get_cricket_events,
    get_cricket_fixtures_today,
    get_cricket_manager,
    get_cricket_player,
    get_cricket_player_events,
    get_cricket_player_statistics,
    get_cricket_players,
    get_cricket_team,
    get_cricket_team_enrichment,
    get_cricket_team_enrichments,
    get_cricket_team_events,
    get_cricket_team_featured_event,
    get_cricket_team_media,
    get_cricket_team_near_events,
    get_cricket_team_performance,
    get_cricket_team_players,
    get_cricket_team_rankings,
    get_cricket_team_standings_seasons,
    get_cricket_team_unique_tournaments,
    get_cricket_teams,
    get_cricket_tournament,
    get_cricket_tournament_events,
    get_cricket_tournament_scheduled_events,
    get_cricket_tournament_seasons,
    get_cricket_tournament_standings,
    get_cricket_tournaments,
    search_cricket,
)


router = APIRouter(
    prefix="/api/v1/cricket",
    tags=["Score Cricket"],
)


async def get_query_params(request: Request) -> dict[str, str]:
    return dict(request.query_params)


@router.get("/events")
async def fetch_cricket_events(
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_events(params=params)


@router.get("/fixtures/today")
async def fetch_cricket_fixtures_today(
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_fixtures_today(params=params)


@router.get("/event/{event_id}")
async def fetch_cricket_event(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event(event_id=event_id, params=params)


@router.get("/event/{event_id}/ball-by-ball")
async def fetch_cricket_event_ball_by_ball(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_ball_by_ball(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/best-players")
async def fetch_cricket_event_best_players(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_best_players(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/enrichments")
async def fetch_cricket_event_enrichments(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_enrichments(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/enrichments/{enrichment_type}")
async def fetch_cricket_event_enrichment(
    event_id: str = Path(..., min_length=1),
    enrichment_type: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_enrichment(
        event_id=event_id,
        enrichment_type=enrichment_type,
        params=params,
    )


@router.get("/event/{event_id}/h2h")
async def fetch_cricket_event_h2h(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_h2h(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/innings")
async def fetch_cricket_event_innings(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_innings(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/odds")
async def fetch_cricket_event_odds(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_odds(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/overs")
async def fetch_cricket_event_overs(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_overs(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/period-scores")
async def fetch_cricket_event_period_scores(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_period_scores(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/pregame-form")
async def fetch_cricket_event_pregame_form(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_pregame_form(
        event_id=event_id,
        params=params,
    )


@router.get("/event/{event_id}/team-streaks")
async def fetch_cricket_event_team_streaks(
    event_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_event_team_streaks(
        event_id=event_id,
        params=params,
    )


@router.get("/teams")
async def fetch_cricket_teams(
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_teams(params=params)


@router.get("/team/{team_id}")
async def fetch_cricket_team(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team(team_id=team_id, params=params)


@router.get("/team/{team_id}/enrichments")
async def fetch_cricket_team_enrichments(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_enrichments(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/enrichments/{enrichment_type}")
async def fetch_cricket_team_enrichment(
    team_id: str = Path(..., min_length=1),
    enrichment_type: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_enrichment(
        team_id=team_id,
        enrichment_type=enrichment_type,
        params=params,
    )


@router.get("/team/{team_id}/events/{direction}")
async def fetch_cricket_team_events(
    team_id: str = Path(..., min_length=1),
    direction: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_events(
        team_id=team_id,
        direction=direction,
        params=params,
    )


@router.get("/team/{team_id}/featured-event")
async def fetch_cricket_team_featured_event(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_featured_event(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/media")
async def fetch_cricket_team_media(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_media(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/near-events")
async def fetch_cricket_team_near_events(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_near_events(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/performance")
async def fetch_cricket_team_performance(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_performance(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/players")
async def fetch_cricket_team_players(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_players(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/rankings")
async def fetch_cricket_team_rankings(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_rankings(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/standings-seasons")
async def fetch_cricket_team_standings_seasons(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_standings_seasons(
        team_id=team_id,
        params=params,
    )


@router.get("/team/{team_id}/unique-tournaments")
async def fetch_cricket_team_unique_tournaments(
    team_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_team_unique_tournaments(
        team_id=team_id,
        params=params,
    )


@router.get("/manager/{manager_id}")
async def fetch_cricket_manager(
    manager_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_manager(
        manager_id=manager_id,
        params=params,
    )


@router.get("/players")
async def fetch_cricket_players(
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_players(params=params)


@router.get("/player/{player_id}")
async def fetch_cricket_player(
    player_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_player(
        player_id=player_id,
        params=params,
    )


@router.get("/player/{player_id}/events/{direction}")
async def fetch_cricket_player_events(
    player_id: str = Path(..., min_length=1),
    direction: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_player_events(
        player_id=player_id,
        direction=direction,
        params=params,
    )


@router.get(
    "/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/statistics"
)
async def fetch_cricket_player_statistics(
    player_id: str = Path(..., min_length=1),
    tournament_id: str = Path(..., min_length=1),
    season_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_player_statistics(
        player_id=player_id,
        tournament_id=tournament_id,
        season_id=season_id,
        params=params,
    )


@router.get("/tournaments")
async def fetch_cricket_tournaments(
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_tournaments(params=params)


@router.get("/unique-tournament/{tournament_id}")
async def fetch_cricket_tournament(
    tournament_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_tournament(
        tournament_id=tournament_id,
        params=params,
    )


@router.get("/unique-tournament/{tournament_id}/events")
async def fetch_cricket_tournament_events(
    tournament_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_tournament_events(
        tournament_id=tournament_id,
        params=params,
    )


@router.get(
    "/unique-tournament/{tournament_id}/scheduled-events/{date}"
)
async def fetch_cricket_tournament_scheduled_events(
    tournament_id: str = Path(..., min_length=1),
    date: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_tournament_scheduled_events(
        tournament_id=tournament_id,
        date=date,
        params=params,
    )


@router.get(
    "/unique-tournament/{tournament_id}/season/{season_id}/standings/{standings_type}"
)
async def fetch_cricket_tournament_standings(
    tournament_id: str = Path(..., min_length=1),
    season_id: str = Path(..., min_length=1),
    standings_type: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_tournament_standings(
        tournament_id=tournament_id,
        season_id=season_id,
        standings_type=standings_type,
        params=params,
    )


@router.get("/unique-tournament/{tournament_id}/seasons")
async def fetch_cricket_tournament_seasons(
    tournament_id: str = Path(..., min_length=1),
    params: dict[str, str] = Depends(get_query_params),
):
    return await get_cricket_tournament_seasons(
        tournament_id=tournament_id,
        params=params,
    )


@router.get("/search")
async def fetch_cricket_search(
    params: dict[str, str] = Depends(get_query_params),
):
    return await search_cricket(params=params)
