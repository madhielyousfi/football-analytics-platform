"""League standings and comparative analytics."""

import plotly.graph_objects as go
import streamlit as st

from dashboard import queries
from dashboard.components.cards import section_header
from dashboard.components.tables import league_table
from dashboard.styles import CYAN, GREEN, VIOLET, plot


def _ranking(frame, field: str, color: str, label: str) -> None:
    ordered = frame.sort_values(field).tail(10)
    fig = go.Figure(go.Bar(
        x=ordered[field], y=ordered["team_name"], orientation="h",
        marker_color=color, hovertemplate=f"%{{y}}: %{{x:.1f}} {label}<extra></extra>",
    ))
    fig.update_xaxes(title=label)
    fig.update_yaxes(tickfont=dict(size=10))
    plot(fig, height=330)


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.markdown('<div class="fi-page-title">League analytics</div>', unsafe_allow_html=True)

    table = queries.league_table(competition_id, season)
    with st.container(border=True):
        section_header("League standings", "Points · goal difference · goals for")
        league_table(table)
    st.caption("This analytical ranking uses simplified tie breaks; official competition rules may differ.")

    comparison = queries.league_comparison(competition_id, season)
    if comparison.empty:
        st.info("League comparisons appear after completed matches.")
        return

    st.write("")
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        section_header("Attack vs defense", "Lower goals against is better")
        fig = go.Figure(go.Scatter(
            x=comparison["goals_for"], y=comparison["goals_against"],
            mode="markers+text", text=comparison["team_name"],
            textposition="top center", textfont=dict(size=9, color="#94A3B8"),
            marker=dict(size=13, color=GREEN, opacity=.8,
                        line=dict(color="#BBF7D0", width=1)),
            hovertemplate="%{text}<br>For %{x} · Against %{y}<extra></extra>",
        ))
        fig.update_xaxes(title="Goals for")
        fig.update_yaxes(title="Goals against", showgrid=True)
        plot(fig, height=390)
    with right, st.container(border=True):
        section_header("Points ranking", "Top 10")
        _ranking(comparison, "points", GREEN, "Points")

    st.write("")
    left, center, right = st.columns(3, gap="medium")
    with left, st.container(border=True):
        section_header("Goals ranking", "Top 10")
        _ranking(comparison, "goals_for", CYAN, "Goals")
    with center, st.container(border=True):
        section_header("Goal difference", "Top 10")
        _ranking(comparison, "goal_difference", VIOLET, "Goal difference")
    with right, st.container(border=True):
        section_header("Win percentage", "Top 10")
        _ranking(comparison, "win_percentage", GREEN, "Win %")

    st.write("")
    with st.container(border=True):
        section_header("Home and away performance", "Wins by venue")
        ordered = comparison.sort_values("home_wins", ascending=False)
        fig = go.Figure()
        fig.add_bar(x=ordered["team_name"], y=ordered["home_wins"],
                    name="Home", marker_color=GREEN)
        fig.add_bar(x=ordered["team_name"], y=ordered["away_wins"],
                    name="Away", marker_color=CYAN)
        fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.12))
        fig.update_xaxes(tickangle=-35, showgrid=False)
        fig.update_yaxes(title="Wins", showgrid=True)
        plot(fig, height=340, showlegend=True)

    st.write("")
    left, center, right = st.columns(3, gap="medium")
    with left, st.container(border=True):
        section_header("Home win rate", "Top 10")
        _ranking(comparison, "home_win_rate", GREEN, "Home win %")
    with center, st.container(border=True):
        section_header("Away win rate", "Top 10")
        _ranking(comparison, "away_win_rate", CYAN, "Away win %")
    with right, st.container(border=True):
        section_header("Best defense", "Fewest goals against")
        defense = comparison.nsmallest(10, "goals_against").sort_values("goals_against", ascending=False)
        fig = go.Figure(go.Bar(
            x=defense["goals_against"], y=defense["team_name"],
            orientation="h", marker_color=VIOLET,
            hovertemplate="%{y}: %{x} conceded<extra></extra>",
        ))
        fig.update_xaxes(title="Goals against")
        fig.update_yaxes(tickfont=dict(size=10))
        plot(fig, height=330)


render()
