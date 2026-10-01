"""Environment based ingestion configuration."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_token: str
    api_base_url: str
    competition: str
    season: int
    duckdb_path: Path
    api_timeout: int = 30
    api_max_retries: int = 3
    refresh_days_back: int = 3
    refresh_days_forward: int = 7
    full_refresh: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load .env and validate values before any API or database work."""
        load_dotenv()
        token = os.getenv("FOOTBALL_API_TOKEN", "").strip()
        if not token:
            raise ValueError("FOOTBALL_API_TOKEN is required; set it in .env")
        competition = os.getenv("FOOTBALL_COMPETITION", "PL").strip().upper()
        if not competition:
            raise ValueError("FOOTBALL_COMPETITION must not be empty")
        season = int(os.getenv("FOOTBALL_SEASON", "2026"))
        if not 2000 <= season <= 2100:
            raise ValueError("FOOTBALL_SEASON must be a plausible start year")
        timeout = int(os.getenv("FOOTBALL_API_TIMEOUT", "30"))
        retries = int(os.getenv("FOOTBALL_API_MAX_RETRIES", "3"))
        days_back = int(os.getenv("FOOTBALL_REFRESH_DAYS_BACK", "3"))
        days_forward = int(os.getenv("FOOTBALL_REFRESH_DAYS_FORWARD", "7"))
        full_refresh_text = os.getenv("FOOTBALL_FULL_REFRESH", "false").strip().lower()
        if full_refresh_text not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("FOOTBALL_FULL_REFRESH must be true or false")
        if timeout < 1 or retries < 0 or days_back < 0 or days_forward < 0:
            raise ValueError("Timeout must be positive; retries and refresh days must be nonnegative")
        return cls(
            api_token=token,
            api_base_url=os.getenv("FOOTBALL_API_BASE_URL", "https://api.football-data.org/v4").rstrip("/"),
            competition=competition,
            season=season,
            duckdb_path=Path(os.getenv("DUCKDB_PATH", "data/football.duckdb")),
            api_timeout=timeout,
            api_max_retries=retries,
            refresh_days_back=days_back,
            refresh_days_forward=days_forward,
            full_refresh=full_refresh_text in {"true", "1", "yes"},
        )
