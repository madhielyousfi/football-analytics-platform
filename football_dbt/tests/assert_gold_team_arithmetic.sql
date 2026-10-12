-- Gold team arithmetic: result columns must reconcile with games played and
-- win percentages must stay within 0-100. One row per violation.

select team_id, competition_id, season, 'wdl_mismatch' as rule
from {{ ref('mart_team_performance') }}
where wins + draws + losses <> matches_played

union all

select team_id, competition_id, season, 'win_percentage_out_of_range'
from {{ ref('mart_team_performance') }}
where win_percentage is not null
    and (win_percentage < 0 or win_percentage > 100)
