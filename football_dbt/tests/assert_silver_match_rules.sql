-- Silver match rules: same-team fixtures, negative goals, and finished
-- matches without scores are data errors. Scheduled/postponed/cancelled
-- matches may carry null scores by design. Statuses are intentionally not
-- pinned to a fixed list (the API can add valid ones); presence is enforced
-- by a not_null schema test on match_status.

with violations as (
    select match_id, 'same home and away team' as rule
    from {{ ref('stg_matches') }}
    where home_team_id is not null and home_team_id = away_team_id

    union all

    select match_id, 'negative goals'
    from {{ ref('stg_matches') }}
    where (home_goals is not null and home_goals < 0)
        or (away_goals is not null and away_goals < 0)

    union all

    select match_id, 'finished match missing scores'
    from {{ ref('stg_matches') }}
    where match_status = 'FINISHED'
        and (home_goals is null or away_goals is null)
)

select * from violations
