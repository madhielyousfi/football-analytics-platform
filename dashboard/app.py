"""Entry point: streamlit run dashboard/app.py"""

import sys
from pathlib import Path

import streamlit as st

# Streamlit places the script directory on sys.path, so add the project root
# for imports shared by this entry point and its pages.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.components.cards import page_header
from dashboard.bootstrap import ensure_or_bootstrap
from dashboard.database import query_frame
from dashboard.queries import competition_seasons, pipeline_runs
from dashboard.styles import inject_styles, relative_time


st.set_page_config(page_title="Football Analytics", page_icon="⚽", layout="wide")
inject_styles()

try:
    with st.spinner("Preparing football analytics data…", show_time=True):
        ensure_or_bootstrap()
except (FileNotFoundError, RuntimeError) as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.markdown(
    '<div class="fi-brand"><span class="fi-mark">⚽</span><div>'
    '<strong>Football Intelligence</strong><small>Analytics platform</small></div></div>',
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/overview.py", title="Overview", icon="📊", default=True),
    st.Page("pages/league.py", title="League", icon="🏆"),
    st.Page("pages/teams.py", title="Teams", icon="👥"),
    st.Page("pages/matches.py", title="Matches", icon="📅"),
    st.Page("pages/head_to_head.py", title="Head-to-Head", icon="⚔️"),
    st.Page("pages/pipeline.py", title="Pipeline", icon="🔄"),
]
# Keep the brand above navigation; Streamlit's default sidebar nav renders first.
page = st.navigation(pages, position="hidden")
for destination in pages:
    st.sidebar.page_link(destination, use_container_width=True)

available = competition_seasons()
if available.empty:
    st.warning("No matches found. Run ingestion, then dbt build.")
    st.stop()

competition_names = dict(zip(available["competition_id"], available["competition_name"]))
competition_ids = sorted(competition_names, key=lambda key: competition_names[key])
st.sidebar.markdown('<div class="fi-sidebar-label">Workspace filters</div>', unsafe_allow_html=True)
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
st.session_state["competition_name"] = competition_names[competition_id]

runs = pipeline_runs(1)
latest_run = None if runs.empty else runs.iloc[0]
st.session_state["latest_run"] = None if latest_run is None else latest_run.to_dict()
st.sidebar.divider()
if st.sidebar.button("↻ Refresh data", width="stretch"):
    query_frame.clear()
    st.rerun()
refreshed = "Unavailable" if latest_run is None else relative_time(latest_run.get("completed_at"))
st.sidebar.caption(f"Data refreshed {refreshed}")

page_header(competition_names[competition_id], int(season), latest_run)
page.run()
