"""Standings and comparative league metrics."""

import plotly.express as px
import streamlit as st

from dashboard import queries


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.title("League analytics")
    st.caption("Simplified standings: points, goal difference, goals for, then name and ID.")
    table = queries.league_table(competition_id, season)
    st.dataframe(table.drop(columns=["team_id"]), hide_index=True, width='stretch')
    comparison = queries.league_comparison(competition_id, season)
    if comparison.empty:
        return
    left, right = st.columns(2)
    with left:
        st.subheader("Points ranking")
        st.plotly_chart(px.bar(comparison, x="points", y="team_name", orientation="h", height=650), width='stretch')
        st.subheader("Goal difference")
        st.plotly_chart(px.bar(comparison, x="goal_difference", y="team_name", orientation="h", height=650), width='stretch')
    with right:
        st.subheader("Goals ranking")
        st.plotly_chart(px.bar(comparison, x="goals_for", y="team_name", orientation="h", height=650), width='stretch')
        st.subheader("Win percentage")
        st.plotly_chart(px.bar(comparison, x="win_percentage", y="team_name", orientation="h", height=650), width='stretch')
    st.subheader("Home and away wins")
    st.plotly_chart(px.bar(comparison, x=["home_wins", "away_wins"], y="team_name",
                           orientation="h", barmode="group", height=650,
                           labels={"value": "Wins", "variable": "Venue"}),
                    width='stretch')
    st.subheader("Home and away win rates")
    st.plotly_chart(px.bar(comparison, x=["home_win_rate", "away_win_rate"], y="team_name",
                           orientation="h", barmode="group", height=650,
                           labels={"value": "Win rate (%)", "variable": "Venue"}),
                    width='stretch')


render()
