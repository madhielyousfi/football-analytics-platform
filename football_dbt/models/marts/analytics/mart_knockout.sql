-- Knockout bracket fixtures for cup tournaments, ordered by round.
-- Any stage that is not a group/regular season is treated as knockout so new
-- competition formats render without code changes (unknown stages sort last).

with knockout as (
    select * from {{ ref('stg_matches') }}
    where stage is not null
        and stage not in ('REGULAR_SEASON', 'GROUP_STAGE', 'LEAGUE_STAGE')
)

select
    k.match_id,
    k.competition_id,
    k.season,
    k.stage,
    case k.stage
        when 'PLAYOFFS' then 5
        when 'LAST_16' then 10
        when 'ROUND_OF_16' then 10
        when 'QUARTER_FINALS' then 20
        when 'SEMI_FINALS' then 30
        when 'THIRD_PLACE' then 35
        when 'FINAL' then 40
        else 99
    end as round_order,
    k.match_date,
    k.match_datetime,
    k.match_status,
    (k.match_status = 'FINISHED'
        and k.home_goals is not null
        and k.away_goals is not null) as is_completed,
    k.home_team_id,
    k.home_team_name,
    home.crest_url as home_crest_url,
    k.away_team_id,
    k.away_team_name,
    away.crest_url as away_crest_url,
    k.home_goals,
    k.away_goals
from knockout as k
left join {{ ref('dim_team') }} as home on k.home_team_id = home.team_id
left join {{ ref('dim_team') }} as away on k.away_team_id = away.team_id
