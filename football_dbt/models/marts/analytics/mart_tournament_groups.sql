-- Group-stage tables for cup tournaments, calculated from completed matches.
-- Official API standings 404 for cups, so positions come from match results
-- (points, goal difference, goals for, team name). Same simplified-tiebreak
-- disclaimer as mart_league_table. Empty for league competitions.

with group_games as (
    select * from {{ ref('stg_matches') }}
    where stage = 'GROUP_STAGE'
        and group_name is not null
        and match_status = 'FINISHED'
        and home_goals is not null
        and away_goals is not null
),

sides as (
    select
        competition_id, season, group_name,
        home_team_id as team_id, home_team_name as team_name,
        home_goals as goals_for, away_goals as goals_against,
        case
            when home_goals > away_goals then 3
            when home_goals = away_goals then 1
            else 0
        end as points
    from group_games

    union all

    select
        competition_id, season, group_name,
        away_team_id, away_team_name,
        away_goals, home_goals,
        case
            when away_goals > home_goals then 3
            when away_goals = home_goals then 1
            else 0
        end
    from group_games
),

aggregated as (
    select
        competition_id, season, group_name, team_id,
        max(team_name) as team_name,
        count(*) as played,
        sum(goals_for) as goals_for,
        sum(goals_against) as goals_against,
        sum(goals_for) - sum(goals_against) as goal_difference,
        sum(points) as points
    from sides
    group by competition_id, season, group_name, team_id
)

select
    competition_id,
    season,
    group_name,
    row_number() over (
        partition by competition_id, season, group_name
        order by points desc, goal_difference desc, goals_for desc, team_name, team_id
    ) as position,
    team_id,
    team_name,
    played,
    goals_for,
    goals_against,
    goal_difference,
    points
from aggregated
