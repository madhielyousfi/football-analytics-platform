"""Compact table presentation for league standings."""

from html import escape

import pandas as pd
import streamlit as st


def _crest(name: str, url: object) -> str:
    """Render source crest URL or a neutral initial placeholder."""
    if isinstance(url, str) and url.startswith(("https://", "http://")):
        return f'<img class="fi-crest" src="{escape(url, quote=True)}" alt="" loading="lazy">'
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
    return f'<span class="fi-initials" aria-hidden="true">{escape(initials)}</span>'


def league_table(frame: pd.DataFrame, *, compact: bool = False) -> None:
    """Render standings from mart_league_table with restrained position marks."""
    if frame.empty:
        st.info("Standings are not available for this selection.")
        return
    shown = frame.head(8) if compact else frame
    total = len(frame)
    rows = []
    for _, row in shown.iterrows():
        position = int(row["position"])
        position_class = "top" if position == 1 else "europe" if position <= 4 else "bottom" if total >= 6 and position > total - 3 else ""
        name = str(row["team_name"])
        crest = _crest(name, row.get("crest_url"))
        cells = "".join(f"<td>{int(row[field])}</td>" for field in
                        ("played", "wins", "draws", "losses", "goal_difference", "points"))
        rows.append(
            f'<tr><td><span class="fi-position {position_class}">{position}</span></td>'
            f'<td><span class="fi-club">{crest}{escape(name)}</span></td>{cells}</tr>'
        )
    st.markdown(
        '<div class="fi-table-wrap"><table class="fi-table"><thead><tr>'
        '<th>#</th><th>Club</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>PTS</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )


def match_table(frame: pd.DataFrame) -> None:
    """Render a scrollable match list with crest fallbacks and actual scores."""
    if frame.empty:
        st.info("No matches match these filters.")
        return
    rows = []
    for _, row in frame.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])
        home_score, away_score = row["home_goals"], row["away_goals"]
        score = "—" if pd.isna(home_score) or pd.isna(away_score) else f"{int(home_score)} – {int(away_score)}"
        day = "—" if pd.isna(row["matchday"]) else str(int(row["matchday"]))
        match_date = pd.Timestamp(row["match_date"]).strftime("%d %b %Y")
        status = str(row["match_status"])
        status_color = (
            "#4ADE80" if status == "FINISHED" else
            "#F59E0B" if status in {"POSTPONED", "SUSPENDED"} else
            "#F87171" if status == "CANCELLED" else "#94A3B8"
        )
        rows.append(
            f'<tr><td>{escape(match_date)}</td>'
            f'<td><span class="fi-club">{_crest(home, row["home_crest_url"])}{escape(home)}</span></td>'
            f'<td><span class="fi-match-score">{escape(score)}</span></td>'
            f'<td><span class="fi-club">{_crest(away, row["away_crest_url"])}{escape(away)}</span></td>'
            f'<td><span style="color:{status_color};font-weight:600">{escape(status)}</span></td>'
            f'<td>{escape(day)}</td></tr>'
        )
    st.markdown(
        '<div class="fi-table-wrap fi-match-list"><table class="fi-table"><thead><tr>'
        '<th>Date</th><th>Home</th><th>Score</th><th>Away</th><th>Status</th><th>Matchday</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )
