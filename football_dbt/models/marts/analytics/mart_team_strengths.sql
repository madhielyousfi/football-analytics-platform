-- Transparent Poisson-style team strengths for predictions.
-- attack_strength = team goals-for/game divided by league average (>1 scores freely).
-- defense_strength = team goals-against/game divided by league average (<1 is solid).
-- Simple season averages, no recency weighting: an interpretable baseline, not xG.

with team_games as (
    select * from {{ ref('int_team_matches') }}
),

league_avg as (
    select
        competition_id,
        season,
        avg(goals_for * 1.0) as avg_goals_per_team_game
    from team_games
    group by competition_id, season
),

team_rates as (
    select
        team_id,
        competition_id,
        season,
        count(*) as played,
        avg(goals_for * 1.0) as goals_for_per_game,
        avg(goals_against * 1.0) as goals_against_per_game,
        avg(case when venue_type = 'HOME' then goals_for * 1.0 end) as home_goals_for_per_game,
        avg(case when venue_type = 'HOME' then goals_against * 1.0 end) as home_goals_against_per_game,
        avg(case when venue_type = 'AWAY' then goals_for * 1.0 end) as away_goals_for_per_game,
        avg(case when venue_type = 'AWAY' then goals_against * 1.0 end) as away_goals_against_per_game
    from team_games
    group by team_id, competition_id, season
)

select
    rates.team_id,
    rates.competition_id,
    rates.season,
    rates.played,
    teams.team_name,
    round(rates.goals_for_per_game, 2) as goals_for_per_game,
    round(rates.goals_against_per_game, 2) as goals_against_per_game,
    round(rates.goals_for_per_game / nullif(lg.avg_goals_per_team_game, 0), 3) as attack_strength,
    round(rates.goals_against_per_game / nullif(lg.avg_goals_per_team_game, 0), 3) as defense_strength,
    round(rates.home_goals_for_per_game / nullif(lg.avg_goals_per_team_game, 0), 3) as home_attack_strength,
    round(rates.home_goals_against_per_game / nullif(lg.avg_goals_per_team_game, 0), 3) as home_defense_strength,
    round(rates.away_goals_for_per_game / nullif(lg.avg_goals_per_team_game, 0), 3) as away_attack_strength,
    round(rates.away_goals_against_per_game / nullif(lg.avg_goals_per_team_game, 0), 3) as away_defense_strength
from team_rates as rates
join league_avg as lg
    on rates.competition_id = lg.competition_id and rates.season = lg.season
left join {{ ref('dim_team') }} as teams on rates.team_id = teams.team_id
