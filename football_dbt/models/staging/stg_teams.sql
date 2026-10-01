with source as (
    select * from {{ source('raw', 'teams') }}
),

ranked as (
    select *, row_number() over (
        partition by team_id order by _ingested_at desc, _batch_id desc
    ) as row_num
    from source
)

select
    cast(team_id as integer) as team_id,
    nullif(trim(name), '') as team_name,
    nullif(trim(short_name), '') as short_name,
    nullif(upper(trim(tla)), '') as tla,
    nullif(trim(country), '') as country,
    cast(founded as integer) as founded,
    nullif(trim(venue), '') as venue,
    nullif(trim(club_colors), '') as club_colors,
    nullif(trim(crest_url), '') as crest_url,
    cast(competition_id as integer) as competition_id,
    cast(_season as integer) as season,
    _ingested_at as ingested_at
from ranked
where row_num = 1
