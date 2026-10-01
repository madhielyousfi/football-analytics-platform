with performance_totals as (
    select competition_id, season,
           sum(matches_played) as team_matches,
           sum(goals_for) as goals,
           sum(points) as points
    from {{ ref('mart_team_performance') }}
    group by competition_id, season
),

fact_totals as (
    select competition_id, season,
           2 * count(*) as team_matches,
           sum(total_goals) as goals,
           sum(home_points + away_points) as points
    from {{ ref('fact_matches') }}
    where is_completed
    group by competition_id, season
)

select coalesce(performance.competition_id, facts.competition_id) as competition_id,
       coalesce(performance.season, facts.season) as season
from performance_totals as performance
full outer join fact_totals as facts
    on performance.competition_id = facts.competition_id
    and performance.season = facts.season
where performance.competition_id is null or facts.competition_id is null
   or performance.team_matches <> facts.team_matches
   or performance.goals <> facts.goals
   or performance.points <> facts.points
