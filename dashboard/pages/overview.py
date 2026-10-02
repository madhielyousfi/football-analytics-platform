"""Executive overview using existing dbt marts."""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import queries
from dashboard.components.cards import form_badges, metric_card, section_header
from dashboard.components.tables import _crest, league_table
from dashboard.styles import CYAN, GREEN, VIOLET, plot, relative_time


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    summary = queries.overview(competition_id, season)
    if summary.empty:
        st.info("Overview metrics are not available for this selection.")
        return
    row = summary.iloc[0]
    values = (
        ("Matches", f'{int(row["total_matches"]):,}', "▦", "green", "Completed matches"),
        ("Goals", f'{int(row["total_goals"]):,}', "⚽", "violet", "Across completed matches"),
        ("Avg Goals", f'{row["average_goals_per_match"]:.2f}', "▥", "cyan", "Per completed match"),
        ("Teams", int(row["number_of_teams"]), "♟", "cyan", "In this competition"),
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
        section_header("🏆  League Standings", "Top 8")
        league_table(table, compact=True)
    with center, st.container(border=True):
        section_header("⌁  Goals Trend", "Per match")
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
            fig.update_yaxes(title=None, showgrid=True)
            plot(fig, height=300)
    with right, st.container(border=True):
        section_header("🎯  Top Attack", "Goals")
        if performance.empty:
            st.info("No completed team results yet.")
        else:
            crests = {str(item["team_name"]): item.get("crest_url") for _, item in table.iterrows()}
            top = performance.nlargest(5, "goals_for")
            maximum = max(1, int(top["goals_for"].max()))
            bars = []
            for index, (_, team) in enumerate(top.iterrows()):
                name = str(team["team_name"])
                goals = int(team["goals_for"])
                width = 100 * goals / maximum
                bars.append(
                    f'<div class="fi-attack-row">{_crest(name, crests.get(name))}'
                    f'<span class="fi-attack-name">{escape(name)}</span>'
                    f'<span class="fi-attack-track"><span class="fi-attack-fill fi-attack-{index}" style="width:{width:.1f}%"></span></span>'
                    f'<strong>{goals}</strong></div>'
                )
            st.markdown('<div class="fi-attack-list">' + ''.join(bars) + '</div>', unsafe_allow_html=True)

    st.write("")
    outcomes = queries.match_outcomes(competition_id, season)
    form = queries.all_team_form(competition_id, season)
    runs = queries.pipeline_runs(1)
    left, center, right = st.columns(3, gap="medium")
    with left, st.container(border=True):
        section_header("⌂  Home vs Away", "Completed results")
        if outcomes.empty or int(outcomes.iloc[0]["total_matches"]) == 0:
            st.info("No completed matches yet.")
        else:
            result = outcomes.iloc[0]
            total = int(result["total_matches"])
            fig = go.Figure(go.Pie(
                labels=["Home wins", "Away wins", "Draws"],
                values=[result["home_wins"], result["away_wins"], result["draws"]],
                hole=.69, marker_colors=[GREEN, "#3B9BFB", "#64748B"],
                textinfo="none",
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            fig.add_annotation(text=f"<b>{total}</b><br>matches", x=.5, y=.5,
                               showarrow=False, font=dict(size=15, color="#F8FAFC"))
            fig.update_layout(legend=dict(orientation="h", y=-.08, x=.5, xanchor="center"))
            plot(fig, height=250, showlegend=True)
    with center, st.container(border=True):
        section_header("⌁  Recent Form", "Last 5 matches")
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
        section_header("▰  Pipeline", "Latest ingestion")
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
