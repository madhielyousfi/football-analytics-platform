with bounds as (
    select
        min(match_date) as first_date,
        max(match_date) as last_date
    from {{ ref('stg_matches') }}
),

dates as (
    select cast(unnest(generate_series(first_date, last_date, interval 1 day)) as date) as date
    from bounds
)

select
    cast(strftime(date, '%Y%m%d') as integer) as date_id,
    date,
    day(date) as day,
    dayname(date) as day_name,
    week(date) as week,
    month(date) as month,
    monthname(date) as month_name,
    quarter(date) as quarter,
    year(date) as year,
    dayofweek(date) in (0, 6) as is_weekend
from dates
