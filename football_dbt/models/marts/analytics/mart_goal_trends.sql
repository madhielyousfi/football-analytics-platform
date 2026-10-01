select
    competition_id,
    season,
    match_date,
    count(*) as matches_played,
    sum(total_goals) as goals,
    sum(home_goals) as home_goals,
    sum(away_goals) as away_goals
from {{ ref('fact_matches') }}
where is_completed
group by competition_id, season, match_date
