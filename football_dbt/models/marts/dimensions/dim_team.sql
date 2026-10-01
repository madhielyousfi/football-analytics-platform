with team_names_from_matches as (
    select home_team_id as team_id, home_team_name as team_name, match_datetime
    from {{ ref('stg_matches') }}
    union all
    select away_team_id as team_id, away_team_name as team_name, match_datetime
    from {{ ref('stg_matches') }}
),

match_team_names as (
    select team_id, arg_max(team_name, match_datetime) as team_name
    from team_names_from_matches
    where team_id is not null
    group by team_id
),

all_team_ids as (
    select team_id from {{ ref('stg_teams') }}
    union
    select team_id from match_team_names
)

select
    ids.team_id,
    coalesce(teams.team_name, names.team_name) as team_name,
    teams.short_name,
    teams.tla,
    teams.country,
    teams.founded,
    teams.venue,
    teams.club_colors,
    teams.crest_url
from all_team_ids as ids
left join {{ ref('stg_teams') }} as teams on ids.team_id = teams.team_id
left join match_team_names as names on ids.team_id = names.team_id
