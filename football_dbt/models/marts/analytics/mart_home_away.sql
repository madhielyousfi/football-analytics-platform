with results as (
    select * from {{ ref('int_team_matches') }}
),

aggregated as (
    select
        team_id,
        competition_id,
        season,
        count(*) filter (where venue_type = 'HOME') as home_matches,
        count(*) filter (where venue_type = 'HOME' and result = 'W') as home_wins,
        count(*) filter (where venue_type = 'HOME' and result = 'D') as home_draws,
        count(*) filter (where venue_type = 'HOME' and result = 'L') as home_losses,
        coalesce(sum(goals_for) filter (where venue_type = 'HOME'), 0) as home_goals_for,
        coalesce(sum(goals_against) filter (where venue_type = 'HOME'), 0) as home_goals_against,
        count(*) filter (where venue_type = 'AWAY') as away_matches,
        count(*) filter (where venue_type = 'AWAY' and result = 'W') as away_wins,
        count(*) filter (where venue_type = 'AWAY' and result = 'D') as away_draws,
        count(*) filter (where venue_type = 'AWAY' and result = 'L') as away_losses,
        coalesce(sum(goals_for) filter (where venue_type = 'AWAY'), 0) as away_goals_for,
        coalesce(sum(goals_against) filter (where venue_type = 'AWAY'), 0) as away_goals_against
    from results
    group by team_id, competition_id, season
)

select
    *,
    round(100.0 * home_wins / nullif(home_matches, 0), 2) as home_win_rate,
    round(100.0 * away_wins / nullif(away_matches, 0), 2) as away_win_rate
from aggregated
