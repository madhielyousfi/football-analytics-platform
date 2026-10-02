"""Head-to-head comparison sourced from dbt marts."""

from html import escape

import plotly.graph_objects as go
import streamlit as st

from dashboard import queries
from dashboard.components.cards import metric_card, section_header
from dashboard.styles import AMBER, CYAN, GREEN, plot


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.markdown('<div class="fi-page-title">Head-to-head</div>', unsafe_allow_html=True)
    options = queries.teams(competition_id, season)
    if len(options) < 2:
        st.info("At least two teams are needed for comparison.")
        return
    labels = dict(zip(options["team_id"], options["team_name"]))
    team_ids = options["team_id"].tolist()
    left, right = st.columns(2, gap="medium")
    team_a = left.selectbox("Team A", team_ids, format_func=lambda key: labels[key])
    team_b = right.selectbox("Team B", team_ids, index=1,
                             format_func=lambda key: labels[key])
    if team_a == team_b:
        st.info("Choose two different teams.")
        return
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:center;gap:1rem;'
        f'padding:1.3rem;background:#111722;border:1px solid rgba(255,255,255,.08);'
        f'border-radius:16px;margin:.5rem 0 1.4rem">'
        f'<strong style="color:#22C55E">{escape(labels[team_a])}</strong>'
        f'<span style="color:#64748B;font-size:.75rem">VS</span>'
        f'<strong style="color:#06B6D4">{escape(labels[team_b])}</strong></div>',
        unsafe_allow_html=True,
    )
    result = queries.head_to_head(competition_id, season, int(team_a), int(team_b))
    if result.empty:
        st.info("No completed meetings for these teams in this season.")
        return
    row = result.iloc[0]
    metrics = (
        ("Meetings", int(row["matches_played"]), "▦", ""),
        (f'{labels[team_a]} wins', int(row["selected_a_wins"]), "▲", "green"),
        ("Draws", int(row["draws"]), "◆", ""),
        (f'{labels[team_b]} wins', int(row["selected_b_wins"]), "▲", "cyan"),
        (f'{labels[team_a]} goals', int(row["selected_a_goals"]), "⚽", "green"),
        (f'{labels[team_b]} goals', int(row["selected_b_goals"]), "⚽", "cyan"),
    )
    for column, (label, value, icon, tone) in zip(st.columns(3), metrics[:3]):
        with column:
            metric_card(label, value, icon=icon, tone=tone)
    st.write("")
    for column, (label, value, icon, tone) in zip(st.columns(3), metrics[3:]):
        with column:
            metric_card(label, value, icon=icon, tone=tone)
    st.write("")

    left, right = st.columns(2, gap="medium")
    names = [labels[team_a], labels[team_b]]
    with left, st.container(border=True):
        section_header("Goals comparison", "Completed meetings")
        fig = go.Figure(go.Bar(
            x=names, y=[row["selected_a_goals"], row["selected_b_goals"]],
            marker_color=[GREEN, CYAN], text=[row["selected_a_goals"], row["selected_b_goals"]],
            textposition="outside",
        ))
        fig.update_yaxes(title="Goals", showgrid=True)
        plot(fig, height=280)
    with right, st.container(border=True):
        section_header("Results split", "Wins and draws")
        fig = go.Figure(go.Pie(
            labels=[f"{names[0]} wins", "Draws", f"{names[1]} wins"],
            values=[row["selected_a_wins"], row["draws"], row["selected_b_wins"]],
            hole=.68, marker_colors=[GREEN, AMBER, CYAN], textinfo="percent",
        ))
        plot(fig, height=280, showlegend=True)

    meetings = queries.head_to_head_matches(
        competition_id, season, int(team_a), int(team_b),
    )
    with st.container(border=True):
        section_header("Recent meetings", "Latest completed matches")
        if meetings.empty:
            st.info("No completed meetings yet.")
        else:
            shown = meetings.rename(columns={
                "match_date": "Date", "home_team": "Home",
                "away_team": "Away", "home_goals": "Home goals",
                "away_goals": "Away goals",
            })
            st.dataframe(shown, hide_index=True, width="stretch")


render()
