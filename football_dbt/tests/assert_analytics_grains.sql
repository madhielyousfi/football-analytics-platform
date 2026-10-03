with all_grains as (
    select 'team_performance' as model, competition_id, season,
           cast(team_id as varchar) as business_key, count(*) as rows_per_key
    from {{ ref('mart_team_performance') }}
    group by competition_id, season, team_id

    union all

    select 'league_table', competition_id, season, cast(team_id as varchar), count(*)
    from {{ ref('mart_league_table') }}
    group by competition_id, season, team_id

    union all

    select 'team_form', competition_id, season, cast(team_id as varchar), count(*)
    from {{ ref('mart_team_form') }}
    group by competition_id, season, team_id

    union all

    select 'home_away', competition_id, season, cast(team_id as varchar), count(*)
    from {{ ref('mart_home_away') }}
    group by competition_id, season, team_id

    union all

    select 'team_strengths', competition_id, season, cast(team_id as varchar), count(*)
    from {{ ref('mart_team_strengths') }}
    group by competition_id, season, team_id

    union all

    select 'tournament_groups', competition_id, season,
           cast(group_name as varchar) || ':' || cast(team_id as varchar), count(*)
    from {{ ref('mart_tournament_groups') }}
    group by competition_id, season, group_name, team_id

    union all

    select 'knockout', competition_id, season, cast(match_id as varchar), count(*)
    from {{ ref('mart_knockout') }}
    group by competition_id, season, match_id

    union all

    select 'goal_analysis', competition_id, season, 'competition', count(*)
    from {{ ref('mart_goal_analysis') }}
    group by competition_id, season

    union all

    select 'head_to_head', competition_id, season,
           cast(team_a_id as varchar) || ':' || cast(team_b_id as varchar), count(*)
    from {{ ref('mart_head_to_head') }}
    group by competition_id, season, team_a_id, team_b_id

    union all

    select 'goal_trends', competition_id, season, cast(match_date as varchar), count(*)
    from {{ ref('mart_goal_trends') }}
    group by competition_id, season, match_date

    union all

    select 'team_progression', competition_id, season,
           cast(team_id as varchar) || ':' || cast(match_id as varchar), count(*)
    from {{ ref('mart_team_progression') }}
    group by competition_id, season, team_id, match_id
)

select * from all_grains where rows_per_key <> 1
