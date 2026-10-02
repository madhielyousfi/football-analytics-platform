"""Cards, badges, headings and form indicators."""

from html import escape

import streamlit as st

from dashboard.styles import relative_time


def metric_card(label: str, value: str | int | float, *, icon: str = "◉",
                tone: str = "", note: str = "") -> None:
    """Render a compact accessible metric card."""
    st.markdown(
        f'<div class="fi-kpi {escape(tone)}"><div class="fi-kpi-head">'
        f'<span>{escape(label)}</span><span class="fi-kpi-icon" aria-hidden="true">{escape(icon)}</span>'
        f'</div><div class="fi-kpi-value">{escape(str(value))}</div>'
        f'<div class="fi-kpi-note">{escape(note) if note else "&nbsp;"}</div></div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, detail: str = "") -> None:
    """Render a consistent heading inside a bordered Streamlit container."""
    st.markdown(
        f'<div class="fi-panel-title">{escape(title)}<span>{escape(detail)}</span></div>',
        unsafe_allow_html=True,
    )


def form_badges(form: object) -> str:
    """Return safe result badges for a dbt mart recent_form value."""
    if not isinstance(form, str) or not form:
        return '<span style="color:#64748B">No results yet</span>'
    badges = "".join(
        f'<span class="{result}" title="{word}">{result}</span>'
        for result, word in ((r, {"W": "Win", "D": "Draw", "L": "Loss"}[r])
                         for r in form.split("-") if r in {"W", "D", "L"})
    )
    return f'<span class="fi-form" aria-label="Recent form {escape(form)}">{badges}</span>'


def pipeline_badge(status: str | None) -> str:
    """Render the latest run state without assuming missing data is healthy."""
    state = (status or "UNKNOWN").upper()
    if state == "SUCCESS":
        return '<span class="fi-status">● Pipeline Healthy</span>'
    if state == "FAILED":
        return '<span class="fi-status failed">● Pipeline Failed</span>'
    return '<span class="fi-status unknown">● Pipeline Unknown</span>'


def page_header(competition_name: str, season: int, latest_run: object) -> None:
    """Render the main header shared by every page."""
    status = None if latest_run is None else latest_run.get("status")
    updated = "Unavailable" if latest_run is None else relative_time(latest_run.get("completed_at"))
    st.markdown(
        '<div class="fi-header"><div><div class="fi-eyebrow">Football intelligence / Analytics</div>'
        f'<h1>{escape(competition_name)} Analytics</h1>'
        f'<div class="fi-subtitle">Season {int(season)} · Last updated {escape(updated)}</div>'
        f'</div>{pipeline_badge(status)}</div>',
        unsafe_allow_html=True,
    )
