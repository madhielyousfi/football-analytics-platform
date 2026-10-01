select staging.match_id
from {{ ref('stg_matches') }} as staging
full outer join {{ ref('fact_matches') }} as facts
    on staging.match_id = facts.match_id
where staging.match_id is null or facts.match_id is null
