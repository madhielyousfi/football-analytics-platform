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
export type LiveFixture = {
  fixture_id: number; league_id: number; league_name: string; season: number; round?: string | null;
  fixture_date: string; status_long?: string | null; status_short?: string | null; elapsed?: number | null;
  home_team_id: number; home_team_name: string; home_crest_url?: string | null;
  away_team_id: number; away_team_name: string; away_crest_url?: string | null;
  goals_home?: number | null; goals_away?: number | null;
};
export type MatchEvent = {
  elapsed?: number | null; extra_minute?: number | null;
  team_id?: number | null; team_name?: string | null;
  player_id?: number | null; player_name?: string | null;
  assist_player_id?: number | null; assist_player_name?: string | null;
  event_type?: string | null; detail?: string | null; comments?: string | null;
};
export type FixtureDetail = {
  fixture: LiveFixture | null;
  events: MatchEvent[];
};
export type LineupRow = {
  team_id: number; team_name: string; formation?: string | null; coach_name?: string | null;
  player_id?: number | null; player_name?: string | null; number?: number | null;
  position?: string | null; grid?: string | null; is_starting: boolean;
};
export type TeamStat = { team_id: number; team_name: string; stat_type: string; stat_value?: string | null };
export type PlayerStatRow = {
  team_id: number; team_name: string; player_id?: number | null; player_name?: string | null;
  number?: number | null; position?: string | null; minutes?: number | null; rating?: string | null;
  goals?: number | null; assists?: number | null; shots_total?: number | null; shots_on?: number | null;
  passes_total?: number | null; passes_key?: number | null; passes_accuracy?: string | null;
  tackles?: number | null; interceptions?: number | null; duels_total?: number | null; duels_won?: number | null;
  dribbles_attempts?: number | null; dribbles_success?: number | null;
  fouls_drawn?: number | null; fouls_committed?: number | null; yellow?: number | null; red?: number | null;
};
export type OddRow = {
  bookmaker_id?: number | null; bookmaker_name?: string | null; bet_id?: number | null;
  bet_name?: string | null; value_name?: string | null; odd?: string | null;
};
