with completed as (
    select * from {{ ref('fact_matches') }} where is_completed
),

ranked as (
    select
        *,
        row_number() over (
            partition by competition_id, season
            order by total_goals desc, match_datetime desc, match_id desc
        ) as goal_rank
    from completed
)

select
    competition_id,
    season,
    count(*) as matches_played,
    sum(total_goals) as total_goals,
    round(avg(total_goals), 2) as average_goals_per_match,
    round(avg(home_goals), 2) as average_home_goals,
    round(avg(away_goals), 2) as average_away_goals,
    count(*) filter (where total_goals > 2) as matches_over_2_5,
    count(*) filter (where total_goals <= 2) as matches_under_2_5,
    count(*) filter (where home_goals = 0 and away_goals = 0) as scoreless_draws,
    max(case when goal_rank = 1 then match_id end) as highest_scoring_match_id,
    max(total_goals) as highest_scoring_match_goals
from ranked
group by competition_id, season
