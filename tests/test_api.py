"""Route-contract tests for the read-only FastAPI layer (no HTTP client needed)."""

from api.main import app, db_path

EXPECTED = {
    "/api/health", "/api/competitions", "/api/teams", "/api/overview",
    "/api/match-outcomes", "/api/league-table", "/api/league-comparison",
    "/api/team-performance", "/api/all-team-form", "/api/team-form",
    "/api/home-away", "/api/goal-trends", "/api/team-progression",
    "/api/match-filter-options", "/api/matches", "/api/head-to-head",
    "/api/head-to-head-matches", "/api/pipeline-runs", "/api/live",
}


def test_all_expected_routes_registered():
    paths = {getattr(r, "path", "") for r in app.routes}
    assert EXPECTED <= paths


def test_db_path_defaults_into_repo():
    assert str(db_path()).endswith("data/football.duckdb")
