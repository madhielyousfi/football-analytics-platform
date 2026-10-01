"""Competition overview: KPIs, table, scoring and goal trends."""

import plotly.express as px
import streamlit as st

from dashboard import queries


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.title("Competition overview")
    st.caption(f"Season {season} · completed-match metrics")

    summary = queries.overview(competition_id, season).iloc[0]
    columns = st.columns(4)
    columns[0].metric("Matches played", int(summary["total_matches"]))
    columns[1].metric("Total goals", int(summary["total_goals"]))
    columns[2].metric("Goals per match", f"{summary['average_goals_per_match']:.2f}")
    columns[3].metric("Teams", int(summary["number_of_teams"]))

    st.subheader("League table")
    table = queries.league_table(competition_id, season)
    st.dataframe(table.drop(columns=["team_id"]), hide_index=True, width='stretch')

    performance = queries.team_performance(competition_id, season)
    if not performance.empty:
        left, right = st.columns(2)
        with left:
            st.subheader("Top scoring teams")
            top = performance.nlargest(10, "goals_for")
            st.plotly_chart(px.bar(top, x="goals_for", y="team_name", orientation="h",
                                   labels={"goals_for": "Goals", "team_name": "Team"}),
                            width='stretch')
        with right:
            st.subheader("Best defenses")
            best = performance.nsmallest(10, "goals_against")
            st.plotly_chart(px.bar(best, x="goals_against", y="team_name", orientation="h",
                                   labels={"goals_against": "Goals conceded", "team_name": "Team"}),
                            width='stretch')

    trends = queries.goal_trends(competition_id, season)
    st.subheader("Goal trends")
    if trends.empty:
        st.info("Goal trends appear after the first completed match.")
    else:
        st.plotly_chart(px.line(trends, x="match_date", y="goals", markers=True,
                                labels={"match_date": "Date (UTC)", "goals": "Goals"}),
                        width='stretch')


render()
