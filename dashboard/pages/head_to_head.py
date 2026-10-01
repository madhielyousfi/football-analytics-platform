"""Comparison between two selected teams."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard import queries


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.title("Head to head")
    options = queries.teams(competition_id, season)
    if len(options) < 2:
        st.info("At least two teams are needed for comparison.")
        return
    labels = dict(zip(options["team_id"], options["team_name"]))
    team_ids = options["team_id"].tolist()
    left, right = st.columns(2)
    team_a = left.selectbox("Team A", team_ids, format_func=lambda key: labels[key])
    team_b = right.selectbox("Team B", team_ids, index=1, format_func=lambda key: labels[key])
    if team_a == team_b:
        st.info("Choose two different teams.")
        return
    result = queries.head_to_head(competition_id, season, int(team_a), int(team_b))
    if result.empty:
        st.info("No completed meetings for these teams in this season.")
        return
    row = result.iloc[0]
    cards = st.columns(4)
    cards[0].metric("Matches", int(row["matches_played"]))
    cards[1].metric(f"{labels[team_a]} wins", int(row["selected_a_wins"]))
    cards[2].metric("Draws", int(row["draws"]))
    cards[3].metric(f"{labels[team_b]} wins", int(row["selected_b_wins"]))

    st.subheader("Goals and wins")
    comparison = pd.DataFrame({
        "Team": [labels[team_a], labels[team_b]],
        "Goals": [row["selected_a_goals"], row["selected_b_goals"]],
        "Wins": [row["selected_a_wins"], row["selected_b_wins"]],
    })
    left, right = st.columns(2)
    left.plotly_chart(px.bar(comparison, x="Team", y="Goals"), width='stretch')
    right.plotly_chart(px.bar(comparison, x="Team", y="Wins"), width='stretch')

    st.subheader("Recent meetings")
    meetings = queries.head_to_head_matches(competition_id, season, int(team_a), int(team_b))
    st.dataframe(meetings, hide_index=True, width='stretch')


render()
