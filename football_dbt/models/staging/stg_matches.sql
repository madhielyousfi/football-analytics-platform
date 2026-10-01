with source as (
    select * from {{ source('raw', 'matches') }}
),

ranked as (
    select *, row_number() over (
        partition by match_id order by _ingested_at desc, _batch_id desc
    ) as row_num
    from source
)

select
    cast(match_id as integer) as match_id,
    cast(competition_id as integer) as competition_id,
    nullif(trim(competition_name), '') as competition_name,
    cast(season_id as integer) as season_id,
    cast(_season as integer) as season,
    cast(season_start_date as date) as season_start_date,
    cast(season_end_date as date) as season_end_date,
    cast(utc_date as timestamptz) as match_datetime,
    cast(utc_date at time zone 'UTC' as date) as match_date,
    nullif(upper(trim(status)), '') as match_status,
    cast(matchday as integer) as matchday,
    nullif(upper(trim(stage)), '') as stage,
    cast(home_team_id as integer) as home_team_id,
    nullif(trim(home_team_name), '') as home_team_name,
    cast(away_team_id as integer) as away_team_id,
    nullif(trim(away_team_name), '') as away_team_name,
    cast(home_score as integer) as home_goals,
    cast(away_score as integer) as away_goals,
    nullif(upper(trim(winner)), '') as winner,
    nullif(upper(trim(duration)), '') as duration,
    _ingested_at as ingested_at
from ranked
where row_num = 1
