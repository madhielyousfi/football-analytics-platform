"""Shared visual system for the Streamlit dashboard."""

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BG = "#080B12"
SURFACE = "#111722"
SURFACE_ALT = "#151D2A"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
GREEN = "#22C55E"
CYAN = "#06B6D4"
VIOLET = "#8B5CF6"
AMBER = "#F59E0B"
RED = "#EF4444"
GRID = "rgba(255,255,255,0.07)"


def inject_styles() -> None:
    """Apply one consistent theme without changing Streamlit's behavior."""
    st.markdown(
        """<style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"], [data-testid="stApp"] {font-family: Inter, sans-serif;}
        [data-testid="stAppViewContainer"] {background: #080B12; color: #F8FAFC;}
        [data-testid="stHeader"] {background: transparent;}
        #MainMenu, footer, [data-testid="stDeployButton"] {visibility:hidden;}
        [data-testid="stMainBlockContainer"] {max-width: 1600px; padding-top: 2rem; padding-bottom: 4rem;}
        [data-testid="stSidebar"] {background: #0D121C; border-right: 1px solid rgba(255,255,255,.08);}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap: .8rem;}
        [data-testid="stSidebarNav"] a {border-radius: 10px; color: #94A3B8; padding: .65rem .85rem;}
        [data-testid="stSidebarNav"] a[aria-current="page"] {background: rgba(34,197,94,.12); color: #F8FAFC; border-left: 3px solid #22C55E;}
        [data-testid="stSidebarNav"] a:hover {background: rgba(255,255,255,.06); color: #F8FAFC;}
        [data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
            background: rgba(17,23,34,.94); backdrop-filter:blur(12px);
            border: 1px solid rgba(255,255,255,.08); border-radius: 16px; padding: 1.15rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 16px;}
        [data-testid="stDataFrame"] {border: 1px solid rgba(255,255,255,.08); border-radius: 12px; overflow: hidden;}
        [data-testid="stDataFrame"] [role="columnheader"] {background: #151D2A; color: #94A3B8;}
        [data-testid="stSelectbox"] > div, [data-testid="stDateInput"] > div {border-radius: 10px;}
        .stButton button {border-radius: 10px; border-color: rgba(255,255,255,.12);}
        h1, h2, h3 {color: #F8FAFC; letter-spacing: -.025em;}
        p, label, .stCaption {color: #94A3B8;}
        .fi-brand {display:flex; align-items:center; gap:.8rem; padding:.4rem .1rem 1rem;}
        .fi-mark {display:grid; place-items:center; width:40px; height:40px; border-radius:12px; background:rgba(34,197,94,.14); color:#22C55E; font-size:1.2rem;}
        .fi-brand strong {display:block; color:#F8FAFC; font-size:1rem; letter-spacing:-.02em;}
        .fi-brand small {display:block; color:#64748B; font-size:.7rem; letter-spacing:.13em; text-transform:uppercase; margin-top:.15rem;}
        .fi-sidebar-label {font-size:.68rem; font-weight:700; letter-spacing:.15em; color:#64748B; text-transform:uppercase; margin-top:1.15rem;}
        .fi-header {display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:1.6rem;}
        .fi-eyebrow {color:#22C55E; font-size:.72rem; font-weight:700; letter-spacing:.17em; text-transform:uppercase; margin-bottom:.45rem;}
        .fi-header h1 {font-size:clamp(1.7rem,3vw,2.6rem); line-height:1.15; margin:0; font-weight:800;}
        .fi-subtitle {color:#94A3B8; margin-top:.55rem; font-size:.88rem;}
        .fi-status {white-space:nowrap; border-radius:999px; padding:.48rem .8rem; font-size:.75rem; font-weight:700; border:1px solid rgba(34,197,94,.25); background:rgba(34,197,94,.1); color:#4ADE80;}
        .fi-status.failed {color:#F87171; background:rgba(239,68,68,.1); border-color:rgba(239,68,68,.25);}
        .fi-status.unknown {color:#94A3B8; background:rgba(148,163,184,.08); border-color:rgba(148,163,184,.18);}
        .fi-page-title {color:#F8FAFC; font-weight:700; font-size:1.16rem; margin:.2rem 0 1rem;}
        .fi-kpi {background:rgba(17,23,34,.94); backdrop-filter:blur(12px); border:1px solid rgba(255,255,255,.08); border-radius:16px; padding:1.15rem 1.25rem; min-height:122px;}
        .fi-kpi-head {display:flex; align-items:center; justify-content:space-between; color:#94A3B8; font-size:.78rem; font-weight:600;}
        .fi-kpi-icon {display:grid; place-items:center; width:29px; height:29px; border-radius:9px; background:rgba(255,255,255,.05); font-size:.9rem;}
        .fi-kpi-value {color:#F8FAFC; font-size:1.75rem; font-weight:800; letter-spacing:-.04em; line-height:1.15; margin-top:.55rem;}
        .fi-kpi-note {color:#64748B; font-size:.72rem; margin-top:.3rem;}
        .fi-kpi.green .fi-kpi-value {color:#4ADE80;}
        .fi-kpi.cyan .fi-kpi-value {color:#22D3EE;}
        .fi-kpi.violet .fi-kpi-value {color:#A78BFA;}
        .fi-panel-title {display:flex; justify-content:space-between; align-items:center; gap:.5rem; color:#F8FAFC; font-weight:700; font-size:.95rem; margin-bottom:.7rem;}
        .fi-panel-title span {color:#64748B; font-weight:500; font-size:.72rem;}
        .fi-table-wrap {overflow-x:auto;}
        .fi-match-list {max-height:650px; overflow:auto;}
        .fi-table {width:100%; border-collapse:collapse; font-size:.77rem;}
        .fi-table th {text-align:right; color:#64748B; font-size:.66rem; letter-spacing:.08em; text-transform:uppercase; font-weight:700; padding:.58rem .35rem; border-bottom:1px solid rgba(255,255,255,.08);}
        .fi-table th:first-child, .fi-table th:nth-child(2) {text-align:left;}
        .fi-table td {text-align:right; color:#CBD5E1; padding:.65rem .35rem; border-bottom:1px solid rgba(255,255,255,.05); white-space:nowrap;}
        .fi-table td:first-child, .fi-table td:nth-child(2) {text-align:left;}
        .fi-table tr:last-child td {border-bottom:0;}
        .fi-club {display:flex; align-items:center; gap:.55rem; color:#F8FAFC; font-weight:600; min-width:115px;}
        .fi-crest, .fi-initials {height:23px; width:23px; object-fit:contain; flex:none;}
        .fi-initials {display:grid; place-items:center; color:#94A3B8; background:#1E293B; border-radius:6px; font-size:.6rem;}
        .fi-position {display:inline-block; border-left:2px solid #334155; padding-left:.4rem; min-width:1.5rem;}
        .fi-position.top {border-color:#22C55E; color:#4ADE80;}
        .fi-position.europe {border-color:#06B6D4; color:#22D3EE;}
        .fi-position.bottom {border-color:#EF4444; color:#F87171;}
        .fi-match-score {display:inline-block; min-width:38px; text-align:center; color:#F8FAFC; background:#1E293B; border-radius:7px; padding:.24rem .35rem; font-weight:700;}
        .fi-form {display:inline-flex; gap:.3rem; align-items:center;}
        .fi-form span {display:grid; place-items:center; width:23px; height:23px; border-radius:50%; font-size:.65rem; font-weight:800; color:#080B12;}
        .fi-form .W {background:#22C55E;} .fi-form .D {background:#F59E0B;} .fi-form .L {background:#EF4444; color:white;}
        .fi-form-row {display:flex; justify-content:space-between; gap:.6rem; align-items:center; padding:.55rem 0; border-bottom:1px solid rgba(255,255,255,.06); font-size:.77rem;}
        .fi-form-row:last-child {border-bottom:0;}
        .fi-form-row strong {color:#F8FAFC; font-weight:600;}
        .fi-architecture {display:flex; flex-wrap:wrap; align-items:center; gap:.45rem; margin:.5rem 0 1rem;}
        .fi-step {padding:.65rem .8rem; border:1px solid rgba(255,255,255,.09); border-radius:10px; background:#151D2A; color:#F8FAFC; font-size:.75rem; font-weight:600;}
        .fi-arrow {color:#22C55E;}
        @media (max-width:900px) {.fi-header {display:block;} .fi-header .fi-status {display:inline-block; margin-top:1rem;} [data-testid="stMainBlockContainer"] {padding:1rem;} .fi-kpi {min-height:105px;}}
        </style>""",
        unsafe_allow_html=True,
    )


def themed_chart(fig: go.Figure, *, height: int = 280, showlegend: bool = False) -> go.Figure:
    """Style a Plotly figure for the shared dark surfaces."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=MUTED, size=11),
        margin=dict(l=8, r=8, t=16, b=8),
        showlegend=showlegend,
        hoverlabel=dict(bgcolor=SURFACE_ALT, font_color=TEXT),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(showgrid=False, zeroline=False, linecolor=GRID)
    return fig


def plot(fig: go.Figure, *, height: int = 280, showlegend: bool = False) -> None:
    """Render a responsive Plotly chart without toolbar clutter."""
    st.plotly_chart(
        themed_chart(fig, height=height, showlegend=showlegend),
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )


def relative_time(value: object) -> str:
    """Describe an actual warehouse timestamp relative to now."""
    if value is None or pd.isna(value):
        return "Unavailable"
    timestamp = pd.Timestamp(value).to_pydatetime()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hr ago"
    return f"{seconds // 86400} d ago"
