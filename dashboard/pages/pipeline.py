"""Operational pipeline observability for the portfolio dashboard."""

from html import escape

import pandas as pd
import streamlit as st

from dashboard import queries
from dashboard.components.cards import metric_card, section_header
from dashboard.styles import relative_time


def _timestamp(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return pd.Timestamp(value).strftime("%d %b %Y · %H:%M UTC")


def _number(value: object) -> str:
    return "—" if value is None or pd.isna(value) else f"{int(value):,}"


def _status(value: object) -> str:
    state = str(value).upper()
    color = "#4ADE80" if state == "SUCCESS" else "#F87171" if state == "FAILED" else "#94A3B8"
    return f'<span style="color:{color};font-weight:700">● {escape(state)}</span>'


def render() -> None:
    st.markdown('<div class="fi-page-title">Data pipeline</div>', unsafe_allow_html=True)
    with st.container(border=True):
        section_header("Architecture", "API to analytics")
        steps = (
            "football-data.org API", "Python ingestion", "DuckDB raw",
            "dbt staging", "dbt intermediate", "Marts", "Streamlit",
        )
        diagram = '<span class="fi-arrow">→</span>'.join(
            f'<span class="fi-step">{escape(step)}</span>' for step in steps
        )
        st.markdown(f'<div class="fi-architecture">{diagram}</div>', unsafe_allow_html=True)
        st.caption("The status below comes from local ingestion metadata. dbt results are validated in CI.")

    runs = queries.pipeline_runs(20)
    if runs.empty:
        st.info("No pipeline run metadata is available. Run ingestion to populate this page.")
        return
    latest = runs.iloc[0]
    successes = runs[runs["status"] == "SUCCESS"]
    last_success = None if successes.empty else successes.iloc[0]
    duration = latest.get("duration_seconds")
    metrics = (
        ("Pipeline status", str(latest["status"]).title(), "●",
         "green" if latest["status"] == "SUCCESS" else ""),
        ("Last successful run", "—" if last_success is None else relative_time(last_success["completed_at"]), "◷", ""),
        ("Rows received", _number(latest["rows_received"]), "▦", "cyan"),
        ("Rows inserted", _number(latest["rows_inserted"]), "↧", "green"),
        ("Rows updated", _number(latest["rows_updated"]), "↻", "violet"),
        ("Execution time", "—" if duration is None or pd.isna(duration) else f"{int(duration)}s", "◴", ""),
    )
    st.write("")
    for column, (label, value, icon, tone) in zip(st.columns(3), metrics[:3]):
        with column:
            metric_card(label, value, icon=icon, tone=tone)
    st.write("")
    for column, (label, value, icon, tone) in zip(st.columns(3), metrics[3:]):
        with column:
            metric_card(label, value, icon=icon, tone=tone)

    st.write("")
    with st.container(border=True):
        section_header("Recent runs", f"{len(runs)} recorded")
        headings = (
            "Run ID", "Started", "Completed", "Duration", "Received",
            "Inserted", "Updated", "Status",
        )
        header = "".join(f"<th>{escape(label)}</th>" for label in headings)
        body = []
        for _, run in runs.iterrows():
            cells = (
                escape(str(run["run_id"])[:8]),
                escape(_timestamp(run["started_at"])),
                escape(_timestamp(run["completed_at"])),
                "—" if pd.isna(run["duration_seconds"]) else f'{int(run["duration_seconds"])}s',
                _number(run["rows_received"]),
                _number(run["rows_inserted"]),
                _number(run["rows_updated"]),
                _status(run["status"]),
            )
            body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
        st.markdown(
            '<div class="fi-table-wrap"><table class="fi-table">'
            f'<thead><tr>{header}</tr></thead><tbody>{"".join(body)}</tbody>'
            '</table></div>', unsafe_allow_html=True,
        )
        if latest["status"] == "FAILED" and pd.notna(latest.get("error_message")):
            st.error(f'Latest error: {latest["error_message"]}')


render()
