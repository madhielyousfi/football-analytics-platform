with ordered as (
    select
        *,
        row_number() over (
            partition by team_id, competition_id, season
            order by match_datetime desc, match_id desc
        ) as recent_rank
    from {{ ref('int_team_matches') }}
),

recent as (
    select * from ordered where recent_rank <= 5
)

select
    team_id,
    competition_id,
    season,
    count(*) as recent_matches,
    count(*) filter (where result = 'W') as wins_last_5,
    count(*) filter (where result = 'D') as draws_last_5,
    count(*) filter (where result = 'L') as losses_last_5,
    sum(points) as points_last_5,
    round(sum(points) / 15.0, 4) as form_score,
    string_agg(result, '-' order by recent_rank) as recent_form
from recent
group by team_id, competition_id, season
