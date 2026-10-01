with ordered as (
    select
        matches.*,
        teams.team_name as opponent_name
    from {{ ref('int_team_matches') }} as matches
    left join {{ ref('dim_team') }} as teams
        on matches.opponent_team_id = teams.team_id
)

select
    match_id,
    competition_id,
    season,
    team_id,
    opponent_team_id,
    opponent_name,
    match_datetime,
    match_date,
    matchday,
    venue_type,
    result,
    goals_for,
    goals_against,
    points,
    sum(goals_for) over (
        partition by competition_id, season, team_id
        order by match_datetime, match_id
        rows between unbounded preceding and current row
    ) as cumulative_goals,
    sum(points) over (
        partition by competition_id, season, team_id
        order by match_datetime, match_id
        rows between unbounded preceding and current row
    ) as cumulative_points
from ordered as matches
