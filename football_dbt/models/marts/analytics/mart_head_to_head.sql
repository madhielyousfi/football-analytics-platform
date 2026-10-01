with match_pairs as (
    select
        competition_id,
        season,
        match_id,
        match_datetime,
        least(home_team_id, away_team_id) as team_a_id,
        greatest(home_team_id, away_team_id) as team_b_id,
        case when home_team_id < away_team_id then home_goals else away_goals end as team_a_goals,
        case when home_team_id < away_team_id then away_goals else home_goals end as team_b_goals
    from {{ ref('fact_matches') }}
    where is_completed
),

ordered as (
    select
        *,
        row_number() over (
            partition by competition_id, season, team_a_id, team_b_id
            order by match_datetime desc, match_id desc
        ) as recent_rank
    from match_pairs
)

select
    competition_id,
    season,
    team_a_id,
    team_b_id,
    count(*) as matches_played,
    count(*) filter (where team_a_goals > team_b_goals) as team_a_wins,
    count(*) filter (where team_a_goals = team_b_goals) as draws,
    count(*) filter (where team_a_goals < team_b_goals) as team_b_wins,
    sum(team_a_goals) as team_a_goals,
    sum(team_b_goals) as team_b_goals,
    string_agg(
        cast(team_a_goals as varchar) || '-' || cast(team_b_goals as varchar),
        ', ' order by recent_rank
    ) filter (where recent_rank <= 5) as recent_results
from ordered
group by competition_id, season, team_a_id, team_b_id
