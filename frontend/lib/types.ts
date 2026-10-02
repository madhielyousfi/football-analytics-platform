export type Competition = {
  competition_id: number;
  competition_name: string;
  competition_code?: string;
  seasons: number[];
};

export type LeagueRow = {
  position: number; team_id: number; team_name: string; crest_url?: string | null;
  short_name?: string | null; played: number; wins: number; draws: number; losses: number;
  goals_for: number; goals_against: number; goal_difference: number; points: number;
};

export type Overview = {
  total_matches: number; total_goals: number; average_goals_per_match: number;
  number_of_teams: number; matches_over_2_5?: number; matches_under_2_5?: number;
  scoreless_draws?: number; average_home_goals?: number; average_away_goals?: number;
};

export type Outcomes = { total_matches: number; home_wins: number; away_wins: number; draws: number };
export type GoalTrend = { match_date: string; matches_played: number; goals: number; home_goals: number; away_goals: number; average_goals: number };
export type TeamFormRow = { team_id: number; team_name: string; crest_url?: string | null; recent_form?: string | null; points_last_5: number; recent_matches?: number | null };
export type TeamPerf = Record<string, number | string | null> & { team_id: number; team_name?: string };
export type HomeAway = Record<string, number | string | null> & { team_id: number; team_name: string };
export type Progression = { match_id: number; match_date: string; match_datetime: string; opponent_name: string; venue_type: string; result: string; goals_for: number; goals_against: number; points: number; cumulative_goals: number; cumulative_points: number };
export type Match = { match_id: number; match_date: string; home_team: string; home_crest_url?: string | null; away_team: string; away_crest_url?: string | null; home_goals?: number | null; away_goals?: number | null; match_status: string; matchday?: number | null };
export type H2H = { matches_played: number; draws: number; selected_a_wins: number; selected_b_wins: number; selected_a_goals: number; selected_b_goals: number; recent_results?: string | null };
export type PipelineRun = { run_id: string; pipeline_name: string; started_at: string; completed_at?: string | null; status: string; rows_received?: number; rows_inserted?: number; rows_updated?: number; error_message?: string | null; duration_seconds?: number | null };
