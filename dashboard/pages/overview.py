"""Executive overview using existing dbt marts."""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries
from dashboard.components.cards import form_badges, metric_card, section_header
from dashboard.components.tables import league_table
from dashboard.styles import CYAN, GREEN, VIOLET, plot, relative_time


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.markdown('<div class="fi-page-title">Overview</div>', unsafe_allow_html=True)

    summary = queries.overview(competition_id, season)
    if summary.empty:
        st.info("Overview metrics are not available for this selection.")
        return
    row = summary.iloc[0]
    values = (
        ("Matches", f'{int(row["total_matches"]):,}', "▦", "green", "Completed matches"),
        ("Goals", f'{int(row["total_goals"]):,}', "⚽", "", "Across completed matches"),
        ("Avg Goals", f'{row["average_goals_per_match"]:.2f}', "↗", "cyan", "Per completed match"),
        ("Teams", int(row["number_of_teams"]), "♟", "violet", "In selected competition"),
    )
    for column, (label, value, icon, tone, note) in zip(st.columns(4), values):
        with column:
            metric_card(label, value, icon=icon, tone=tone, note=note)

    st.write("")
    table = queries.league_table(competition_id, season)
    trends = queries.goal_trends(competition_id, season)
    performance = queries.team_performance(competition_id, season)
    left, center, right = st.columns([1.35, 1.2, 1], gap="medium")
    with left, st.container(border=True):
        section_header("League standings", "Top 8")
        league_table(table, compact=True)
    with center, st.container(border=True):
        section_header("Goals trend", "Average per match day")
        if trends.empty:
            st.info("Goal trends appear after completed matches.")
        else:
            fig = go.Figure(go.Scatter(
                x=trends["match_date"], y=trends["average_goals"],
                mode="lines+markers", line=dict(color=GREEN, width=3),
                marker=dict(color=GREEN, size=6, line=dict(color="#BBF7D0", width=1)),
                fill="tozeroy", fillcolor="rgba(34,197,94,0.06)",
                hovertemplate="%{x|%b %d}<br>%{y:.2f} avg goals<extra></extra>",
            ))
            fig.update_yaxes(title="Goals / match")
            plot(fig, height=300)
    with right, st.container(border=True):
        section_header("Top attack", "Goals scored")
        if performance.empty:
            st.info("No completed team results yet.")
        else:
            top = performance.nlargest(7, "goals_for").sort_values("goals_for")
            fig = go.Figure(go.Bar(
                x=top["goals_for"], y=top["team_name"], orientation="h",
                marker_color=[GREEN, CYAN, VIOLET, GREEN, CYAN, VIOLET, GREEN][:len(top)],
                text=top["goals_for"], textposition="outside",
                hovertemplate="%{y}: %{x} goals<extra></extra>",
            ))
            fig.update_xaxes(title=None)
            fig.update_yaxes(tickfont=dict(size=10))
            plot(fig, height=300)

    st.write("")
    outcomes = queries.match_outcomes(competition_id, season)
    form = queries.all_team_form(competition_id, season)
    runs = queries.pipeline_runs(1)
    left, center, right = st.columns(3, gap="medium")
    with left, st.container(border=True):
        section_header("Home vs away", "Completed results")
        if outcomes.empty or int(outcomes.iloc[0]["total_matches"]) == 0:
            st.info("No completed matches yet.")
        else:
            result = outcomes.iloc[0]
            total = int(result["total_matches"])
            fig = go.Figure(go.Pie(
                labels=["Home wins", "Away wins", "Draws"],
                values=[result["home_wins"], result["away_wins"], result["draws"]],
                hole=.73, marker_colors=[GREEN, CYAN, "#64748B"],
                textinfo="percent", textposition="outside",
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            fig.add_annotation(text=f"<b>{total}</b><br>matches", x=.5, y=.5,
                               showarrow=False, font=dict(size=15, color="#F8FAFC"))
            fig.update_layout(legend=dict(orientation="h", y=-.1, x=.5, xanchor="center"))
            plot(fig, height=260, showlegend=True)
    with center, st.container(border=True):
        section_header("Recent form", "Last 5 finished matches")
        if form.empty:
            st.info("Form appears after completed matches.")
        else:
            rows = "".join(
                '<div class="fi-form-row">'
                f'<strong>{escape(str(team["team_name"]))}</strong>{form_badges(team["recent_form"])}'
                '</div>'
                for _, team in form.head(7).iterrows()
            )
            st.markdown(rows, unsafe_allow_html=True)
    with right, st.container(border=True):
        section_header("Pipeline summary", "Latest ingestion")
        if runs.empty:
            st.info("No pipeline run metadata is available.")
        else:
            latest = runs.iloc[0]
            elapsed = latest.get("duration_seconds")
            received = latest.get("rows_received")
            details = (
                ("Last run", relative_time(latest.get("completed_at"))),
                ("Data processed", "—" if pd.isna(received) else f'{int(received):,} rows'),
                ("Execution time", "—" if pd.isna(elapsed) else f"{int(elapsed)}s"),
                ("Pipeline", str(latest["status"]).title()),
            )
            for label, value in details:
                st.markdown(
                    f'<div class="fi-form-row"><span>{escape(label)}</span>'
                    f'<strong>{escape(value)}</strong></div>', unsafe_allow_html=True,
                )
            st.caption("Local warehouse metadata · refresh to see new runs")


render()
