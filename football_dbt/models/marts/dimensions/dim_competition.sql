select
    competition_id,
    competition_name,
    competition_code,
    competition_type,
    country,
    year(current_season_start_date) as season,
    current_season_start_date as season_start_date,
    current_season_end_date as season_end_date
from {{ ref('stg_competitions') }}
