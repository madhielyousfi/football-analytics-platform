with completed as (
    select * from {{ ref('int_match_results') }}
    where is_completed
),

team_sides as (
    select
        match_id, competition_id, season_id, season, match_datetime,
        match_date, matchday,
        home_team_id as team_id,
        away_team_id as opponent_team_id,
        'HOME' as venue_type,
        home_goals as goals_for,
        away_goals as goals_against,
        home_points as points
    from completed

    union all

    select
        match_id, competition_id, season_id, season, match_datetime,
        match_date, matchday,
        away_team_id as team_id,
        home_team_id as opponent_team_id,
        'AWAY' as venue_type,
        away_goals as goals_for,
        home_goals as goals_against,
        away_points as points
    from completed
)

select
    match_id,
    team_id,
    opponent_team_id,
    competition_id,
    season_id,
    season,
    match_datetime,
    match_date,
    matchday,
    venue_type,
    goals_for,
    goals_against,
    goals_for - goals_against as goal_difference,
    case
        when goals_for > goals_against then 'W'
        when goals_for = goals_against then 'D'
        else 'L'
    end as result,
    points
from team_sides
