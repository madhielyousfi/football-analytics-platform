"""Filtered match explorer with source team crests."""

import pandas as pd
import streamlit as st

from dashboard import queries
from dashboard.components.cards import section_header
from dashboard.components.tables import match_table


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.markdown('<div class="fi-page-title">Match explorer</div>', unsafe_allow_html=True)
    st.caption("Competition and season filters are available in the sidebar.")
    team_options = queries.teams(competition_id, season)
    team_labels = dict(zip(team_options["team_id"], team_options["team_name"]))
    dates, matchdays, statuses = queries.match_filter_options(competition_id, season)
    if dates.empty or pd.isna(dates.iloc[0]["min_date"]):
        st.info("No matches are available for this season.")
        return

    first = st.columns([1.3, 1, 1], gap="medium")
    team_id = first[0].selectbox(
        "Team", [None, *team_options["team_id"].tolist()],
        format_func=lambda key: "All teams" if key is None else team_labels[key],
    )
    matchday = first[1].selectbox(
        "Matchday", [None, *matchdays["matchday"].tolist()],
        format_func=lambda value: "All matchdays" if value is None else str(value),
    )
    status = first[2].selectbox(
        "Status", [None, *statuses["match_status"].dropna().tolist()],
        format_func=lambda value: "All statuses" if value is None else value,
    )
    min_date = dates.iloc[0]["min_date"].date()
    max_date = dates.iloc[0]["max_date"].date()
    selected_dates = st.date_input(
        "Date range (UTC)", value=(min_date, max_date),
        min_value=min_date, max_value=max_date,
    )
    if len(selected_dates) != 2:
        st.info("Choose a start and end date.")
        return
    start_date, end_date = selected_dates
    result = queries.matches(
        competition_id, season, None if team_id is None else int(team_id),
        None if matchday is None else int(matchday), start_date, end_date, status,
    )
    with st.container(border=True):
        section_header("Matches", f"{len(result):,} results")
        match_table(result)


render()
