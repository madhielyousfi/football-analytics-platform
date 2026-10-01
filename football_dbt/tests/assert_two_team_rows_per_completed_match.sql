with counts as (
    select match_id, count(*) as team_rows,
           count(distinct team_id) as distinct_teams
    from {{ ref('int_team_matches') }}
    group by match_id
)

select results.match_id
from {{ ref('int_match_results') }} as results
left join counts on results.match_id = counts.match_id
where (results.is_completed and (coalesce(counts.team_rows, 0) <> 2 or counts.distinct_teams <> 2))
   or (not results.is_completed and counts.team_rows is not null)
