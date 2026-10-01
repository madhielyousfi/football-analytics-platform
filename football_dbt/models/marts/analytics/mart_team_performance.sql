with team_results as (
    select * from {{ ref('int_team_matches') }}
),

aggregated as (
    select
        team_id,
        competition_id,
        season,
        count(*) as matches_played,
        count(*) filter (where result = 'W') as wins,
        count(*) filter (where result = 'D') as draws,
        count(*) filter (where result = 'L') as losses,
        sum(goals_for) as goals_for,
        sum(goals_against) as goals_against,
        sum(goal_difference) as goal_difference,
        sum(points) as points
    from team_results
    group by team_id, competition_id, season
)

select
    results.*,
    teams.team_name,
    round(100.0 * wins / nullif(matches_played, 0), 2) as win_percentage,
    round(goals_for * 1.0 / nullif(matches_played, 0), 2) as goals_per_game,
    round(goals_against * 1.0 / nullif(matches_played, 0), 2) as goals_conceded_per_game,
    round(points * 1.0 / nullif(matches_played, 0), 2) as points_per_game
from aggregated as results
left join {{ ref('dim_team') }} as teams on results.team_id = teams.team_id
