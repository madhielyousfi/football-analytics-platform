"""Read-only DuckDB access for Streamlit pages."""

from contextlib import closing
import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def database_path() -> Path:
    """Resolve the configured database relative to the repository root."""
    configured = Path(os.getenv("DUCKDB_PATH", "data/football.duckdb"))
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def ensure_analytics_ready() -> None:
    """Raise an actionable error if ingestion or dbt build has not run."""
    path = database_path()
    if not path.is_file():
        raise FileNotFoundError(f"DuckDB file not found: {path}. Run ingestion and dbt build first.")
    with closing(duckdb.connect(str(path), read_only=True)) as connection:
        count = connection.execute("""SELECT count(*) FROM information_schema.tables
            WHERE table_schema = 'marts' AND table_name = 'fact_matches'""").fetchone()[0]
    if count == 0:
        raise RuntimeError("dbt marts are missing. Run dbt build before the dashboard.")


@st.cache_data(ttl=300, show_spinner=False)
def query_frame(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a fixed, parameterized SELECT and cache its data briefly."""
    with closing(duckdb.connect(str(database_path()), read_only=True)) as connection:
        return connection.execute(sql, list(params)).fetchdf()
