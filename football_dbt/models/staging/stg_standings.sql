with source as (
    select * from {{ source('raw', 'standings') }}
),

ranked as (
    select *, row_number() over (
        partition by standing_key order by _ingested_at desc, _batch_id desc
    ) as row_num
    from source
)

select
    standing_key,
    cast(competition_id as integer) as competition_id,
    cast(season_id as integer) as season_id,
    cast(_season as integer) as season,
    cast(team_id as integer) as team_id,
    nullif(trim(team_name), '') as team_name,
    nullif(upper(trim(standing_type)), '') as standing_type,
    nullif(upper(trim(stage)), '') as stage,
    nullif(upper(trim(group_name)), '') as group_name,
    cast(position as integer) as position,
    cast(played_games as integer) as played_games,
    cast(won as integer) as wins,
    cast(draw as integer) as draws,
    cast(lost as integer) as losses,
    cast(points as integer) as points,
    cast(goals_for as integer) as goals_for,
    cast(goals_against as integer) as goals_against,
    cast(goal_difference as integer) as goal_difference,
    nullif(trim(form), '') as form,
    _ingested_at as ingested_at
from ranked
where row_num = 1
