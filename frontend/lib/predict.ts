/** Dixon-Coles-lite Poisson match predictor (no rho correction).
 *
 *  lambda_home = homeAttack(home) * awayDefense(away) * avgHomeGoals
 *  lambda_away = awayAttack(away) * homeDefense(home) * avgAwayGoals
 *  Probabilities come from the independent-Poisson scoreline matrix (0..10).
 *  Transparent baseline from season averages — not xG, no recency weighting.
 */

export type Strengths = {
  attack_strength: number;
  defense_strength: number;
  home_attack_strength: number;
  home_defense_strength: number;
  away_attack_strength: number;
  away_defense_strength: number;
};

export type Prediction = {
  lambdaHome: number;
  lambdaAway: number;
  homeWin: number;
  draw: number;
  awayWin: number;
  over25: number;
  btts: number;
  topScores: { hg: number; ag: number; p: number }[];
};

function factorial(n: number): number {
  let r = 1;
  for (let i = 2; i <= n; i++) r *= i;
  return r;
}

export function poisson(k: number, lambda: number): number {
  return (Math.exp(-lambda) * Math.pow(lambda, k)) / factorial(k);
}

function num(v: unknown, fallback: number): number {
  const n = Number(v);
  return v === null || v === undefined || !Number.isFinite(n) ? fallback : n;
}

export function predict(
  home: Strengths,
  away: Strengths,
  avgHomeGoals: number,
  avgAwayGoals: number,
): Prediction | null {
  if (!Number.isFinite(avgHomeGoals) || !Number.isFinite(avgAwayGoals) || avgHomeGoals <= 0) {
    return null;
  }
  const lambdaHome = num(home.home_attack_strength, 1) * num(away.away_defense_strength, 1) * avgHomeGoals;
  const lambdaAway = num(away.away_attack_strength, 1) * num(home.home_defense_strength, 1) * avgAwayGoals;
  const matrix: number[][] = [];
  for (let hg = 0; hg <= 10; hg++) {
    matrix[hg] = [];
    for (let ag = 0; ag <= 10; ag++) matrix[hg][ag] = poisson(hg, lambdaHome) * poisson(ag, lambdaAway);
  }
  let homeWin = 0;
  let draw = 0;
  let awayWin = 0;
  let over25 = 0;
  let btts = 0;
  const scores: { hg: number; ag: number; p: number }[] = [];
  for (let hg = 0; hg <= 10; hg++) {
    for (let ag = 0; ag <= 10; ag++) {
      const p = matrix[hg][ag];
      if (hg > ag) homeWin += p;
      else if (hg === ag) draw += p;
      else awayWin += p;
      if (hg + ag >= 3) over25 += p;
      if (hg >= 1 && ag >= 1) btts += p;
      scores.push({ hg, ag, p });
    }
  }
  scores.sort((a, b) => b.p - a.p);
  const round3 = (n: number) => Math.round(n * 1000) / 1000;
  return {
    lambdaHome: round3(lambdaHome),
    lambdaAway: round3(lambdaAway),
    homeWin: round3(homeWin),
    draw: round3(draw),
    awayWin: round3(awayWin),
    over25: round3(over25),
    btts: round3(btts),
    topScores: scores.slice(0, 3).map((s) => ({ ...s, p: round3(s.p) })),
  };
}

export function pct(p: number): string {
  return `${Math.round(p * 100)}%`;
}
