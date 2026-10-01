"""Entry point: streamlit run dashboard/app.py"""

import sys
from pathlib import Path

import streamlit as st

# Streamlit places the script directory on sys.path, so add the project root
# for imports shared by this entry point and its pages.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.database import ensure_analytics_ready, query_frame
from dashboard.queries import competition_seasons


st.set_page_config(page_title="Football Analytics", page_icon="⚽", layout="wide")

try:
    ensure_analytics_ready()
except (FileNotFoundError, RuntimeError) as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.title("⚽ Football Analytics")
if st.sidebar.button("Refresh data"):
    query_frame.clear()
    st.rerun()

available = competition_seasons()
if available.empty:
    st.warning("No matches found. Run ingestion, then dbt build.")
    st.stop()

competition_names = dict(zip(available["competition_id"], available["competition_name"]))
competition_ids = sorted(competition_names, key=lambda key: competition_names[key])
competition_id = st.sidebar.selectbox(
    "Competition", competition_ids,
    format_func=lambda key: competition_names[key],
)
season_options = sorted(
    available.loc[available["competition_id"] == competition_id, "season"].unique(),
    reverse=True,
)
season = st.sidebar.selectbox("Season", season_options)
st.session_state["competition_id"] = int(competition_id)
st.session_state["season"] = int(season)
st.sidebar.caption("Dashboard queries dbt marts. Refresh after a new dbt build.")

page = st.navigation([
    st.Page("pages/overview.py", title="Overview", icon="📊", default=True),
    st.Page("pages/teams.py", title="Teams", icon="👥"),
    st.Page("pages/matches.py", title="Matches", icon="📅"),
    st.Page("pages/league.py", title="League", icon="🏆"),
    st.Page("pages/head_to_head.py", title="Head to Head", icon="⚔️"),
])
page.run()
