with source as (
    select * from {{ source('raw', 'competitions') }}
),

ranked as (
    select *, row_number() over (
        partition by competition_id order by _ingested_at desc, _batch_id desc
    ) as row_num
    from source
)

select
    cast(competition_id as integer) as competition_id,
    nullif(trim(name), '') as competition_name,
    nullif(upper(trim(code)), '') as competition_code,
    nullif(upper(trim(type)), '') as competition_type,
    nullif(trim(area_name), '') as country,
    cast(current_season_id as integer) as current_season_id,
    try_cast(json_extract_string(_payload, '$.currentSeason.startDate') as date) as current_season_start_date,
    try_cast(json_extract_string(_payload, '$.currentSeason.endDate') as date) as current_season_end_date,
    _ingested_at as ingested_at
from ranked
where row_num = 1
