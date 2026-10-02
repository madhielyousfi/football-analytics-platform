"""Team analytics with form, progression and venue splits."""

from html import escape

import plotly.graph_objects as go
import streamlit as st

from dashboard import queries
from dashboard.components.cards import form_badges, metric_card, section_header
from dashboard.styles import AMBER, CYAN, GREEN, RED, VIOLET, plot


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    options = queries.teams(competition_id, season)
    st.markdown('<div class="fi-page-title">Team analytics</div>', unsafe_allow_html=True)
    if options.empty:
        st.info("No teams are available for this season.")
        return
    labels = dict(zip(options["team_id"], options["team_name"]))
    team_id = st.selectbox("Select team", options["team_id"].tolist(),
                           format_func=lambda key: labels[key])
    name = labels[team_id]
    st.markdown(
        f'<div class="fi-eyebrow">Team intelligence</div>'
        f'<h2 style="margin:.1rem 0 .3rem">{escape(name)}</h2>'
        f'<div class="fi-subtitle">{escape(st.session_state["competition_name"])} · Season {season}</div>',
        unsafe_allow_html=True,
    )

    form = queries.team_form(competition_id, season, int(team_id))
    if not form.empty:
        current = form.iloc[0]
        st.markdown(
            f'<div style="margin:1rem 0">Recent form&nbsp;&nbsp;{form_badges(current["recent_form"])}'
            f'&nbsp;&nbsp;<span style="color:#94A3B8;font-size:.78rem">'
            f'{int(current["points_last_5"])} points in {int(current["recent_matches"])} matches</span></div>',
            unsafe_allow_html=True,
        )

    performance = queries.team_performance(competition_id, season, int(team_id))
    if performance.empty:
        st.info("Completed match statistics will appear after this team plays.")
        return
    row = performance.iloc[0]
    metrics = (
        ("Matches", int(row["matches_played"]), "▦", ""),
        ("Wins", int(row["wins"]), "▲", "green"),
        ("Draws", int(row["draws"]), "◆", ""),
        ("Losses", int(row["losses"]), "▼", ""),
        ("Points", int(row["points"]), "✦", "green"),
        ("Goals for", int(row["goals_for"]), "⚽", "cyan"),
        ("Goals against", int(row["goals_against"]), "◌", ""),
        ("Win rate", f'{row["win_percentage"]:.1f}%', "↗", "violet"),
    )
    for group in (metrics[:4], metrics[4:]):
        for column, (label, value, icon, tone) in zip(st.columns(4), group):
            with column:
                metric_card(label, value, icon=icon, tone=tone)
        st.write("")

    progression = queries.team_progression(competition_id, season, int(team_id))
    split = queries.home_away(competition_id, season, int(team_id))
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        section_header("Cumulative points", "Season progression")
        if progression.empty:
            st.info("No completed match progression.")
        else:
            fig = go.Figure(go.Scatter(
                x=progression["match_date"], y=progression["cumulative_points"],
                mode="lines+markers", line=dict(color=GREEN, width=3),
                marker=dict(size=6, color=GREEN),
                hovertemplate="%{x|%b %d}: %{y} points<extra></extra>",
            ))
            fig.update_yaxes(title="Points")
            plot(fig, height=300)
    with right, st.container(border=True):
        section_header("Goals scored vs conceded", "Per match")
        if progression.empty:
            st.info("No completed match goals.")
        else:
            fig = go.Figure()
            fig.add_bar(x=progression["match_date"], y=progression["goals_for"],
                        name="Scored", marker_color=GREEN)
            fig.add_bar(x=progression["match_date"], y=progression["goals_against"],
                        name="Conceded", marker_color=CYAN)
            fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.1))
            fig.update_yaxes(title="Goals", showgrid=True)
            plot(fig, height=300, showlegend=True)

    st.write("")
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        section_header("Home vs away", "Season split")
        if split.empty:
            st.info("Venue splits are not available.")
        else:
            venue = split.iloc[0]
            fig = go.Figure()
            for field, label, color in (
                ("home_wins", "Wins", GREEN),
                ("home_draws", "Draws", AMBER),
                ("home_losses", "Losses", RED),
            ):
                fig.add_bar(x=["Home", "Away"],
                            y=[venue[field], venue[field.replace("home_", "away_")]],
                            name=label, marker_color=color)
            fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.1))
            fig.update_yaxes(title="Matches", showgrid=True)
            plot(fig, height=260, showlegend=True)
    with right, st.container(border=True):
        section_header("Cumulative goals", "Season progression")
        if progression.empty:
            st.info("No completed goal progression.")
        else:
            fig = go.Figure(go.Scatter(
                x=progression["match_date"], y=progression["cumulative_goals"],
                mode="lines+markers", line=dict(color=VIOLET, width=3),
                marker=dict(color=VIOLET, size=6),
                hovertemplate="%{x|%b %d}: %{y} goals<extra></extra>",
            ))
            fig.update_yaxes(title="Goals")
            plot(fig, height=260)

    st.write("")
    with st.container(border=True):
        section_header("Performance trend", "Points earned per match")
        if progression.empty:
            st.info("No completed results yet.")
        else:
            fig = go.Figure(go.Scatter(
                x=progression["match_date"], y=progression["points"],
                mode="lines+markers", line=dict(color=CYAN, width=2),
                marker=dict(color=CYAN, size=7),
                hovertemplate="%{x|%b %d}: %{y} points<extra></extra>",
            ))
            fig.update_yaxes(title="Points", tickvals=[0, 1, 3], range=[-.2, 3.3])
            plot(fig, height=230)

    with st.container(border=True):
        section_header("Recent results", "Latest completed matches")
        if progression.empty:
            st.info("No completed matches yet.")
        else:
            recent = progression.tail(8).iloc[::-1]
            shown = recent[["match_date", "opponent_name", "venue_type", "result",
                            "goals_for", "goals_against", "points"]].rename(columns={
                "match_date": "Date", "opponent_name": "Opponent",
                "venue_type": "Venue", "result": "Result", "goals_for": "GF",
                "goals_against": "GA", "points": "Points",
            })
            st.dataframe(shown, hide_index=True, width="stretch")


render()
