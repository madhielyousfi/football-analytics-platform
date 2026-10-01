with participants as (
    select competition_id, season, home_team_id as team_id
    from {{ ref('stg_matches') }}
    union
    select competition_id, season, away_team_id as team_id
    from {{ ref('stg_matches') }}
),

standings as (
    select
        participants.competition_id,
        participants.season,
        participants.team_id,
        teams.team_name,
        coalesce(performance.matches_played, 0) as played,
        coalesce(performance.wins, 0) as wins,
        coalesce(performance.draws, 0) as draws,
        coalesce(performance.losses, 0) as losses,
        coalesce(performance.goals_for, 0) as goals_for,
        coalesce(performance.goals_against, 0) as goals_against,
        coalesce(performance.goal_difference, 0) as goal_difference,
        coalesce(performance.points, 0) as points
    from participants
    left join {{ ref('dim_team') }} as teams
        on participants.team_id = teams.team_id
    left join {{ ref('mart_team_performance') }} as performance
        on participants.team_id = performance.team_id
        and participants.competition_id = performance.competition_id
        and participants.season = performance.season
)

select
    row_number() over (
        partition by competition_id, season
        order by points desc, goal_difference desc, goals_for desc, team_name, team_id
    ) as position,
    *
from standings
