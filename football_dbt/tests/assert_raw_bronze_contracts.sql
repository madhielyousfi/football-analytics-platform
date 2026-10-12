-- Bronze contract: every raw record carries its business key, source labels,
-- ingestion timestamp, and a payload. One row per violation; empty = pass.

with violations as (
    select match_id as record_id, 'matches' as source_table, 'match_id' as field
    from {{ source('raw', 'matches') }}
    where match_id is null
        or _payload is null or _ingested_at is null
        or _source is null or _batch_id is null

    union all

    select team_id, 'teams', 'team_id'
    from {{ source('raw', 'teams') }}
    where team_id is null
        or _payload is null or _ingested_at is null
        or _source is null or _batch_id is null

    union all

    select competition_id, 'competitions', 'competition_id'
    from {{ source('raw', 'competitions') }}
    where competition_id is null
        or _payload is null or _ingested_at is null
        or _source is null or _batch_id is null

    union all

    select standing_key, 'standings', 'standing_key'
    from {{ source('raw', 'standings') }}
    where standing_key is null
        or _payload is null or _ingested_at is null
        or _source is null or _batch_id is null
)

select * from violations
