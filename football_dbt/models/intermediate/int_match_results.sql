with matches as (
    select * from {{ ref('stg_matches') }}
),

results as (
    select
        *,
        match_status = 'FINISHED'
            and home_goals is not null
            and away_goals is not null as is_completed
    from matches
)

select
    match_id,
    competition_id,
    season_id,
    season,
    match_datetime,
    match_date,
    match_status,
    matchday,
    home_team_id,
    away_team_id,
    home_goals,
    away_goals,
    is_completed,
    case when is_completed then home_goals + away_goals end as total_goals,
    case when is_completed then home_goals - away_goals end as goal_difference,
    case
        when is_completed and home_goals > away_goals then 3
        when is_completed and home_goals = away_goals then 1
        when is_completed then 0
    end as home_points,
    case
        when is_completed and away_goals > home_goals then 3
        when is_completed and away_goals = home_goals then 1
        when is_completed then 0
    end as away_points,
    case
        when is_completed and home_goals > away_goals then home_team_id
        when is_completed and away_goals > home_goals then away_team_id
    end as winner_team_id,
    case when is_completed then home_goals = away_goals end as is_draw,
    case when is_completed then home_goals > away_goals end as is_home_win,
    case when is_completed then away_goals > home_goals end as is_away_win
from results
