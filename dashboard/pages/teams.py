"""Team performance and progression page."""

import plotly.express as px
import streamlit as st

from dashboard import queries


def render() -> None:
    competition_id = st.session_state["competition_id"]
    season = st.session_state["season"]
    st.title("Team analytics")
    options = queries.teams(competition_id, season)
    if options.empty:
        st.info("No teams are available for this season.")
        return
    labels = dict(zip(options["team_id"], options["team_name"]))
    team_id = st.selectbox("Team", options["team_id"].tolist(), format_func=lambda key: labels[key])

    performance = queries.team_performance(competition_id, season, int(team_id))
    if performance.empty:
        st.info("No completed matches for this team yet.")
        return
    row = performance.iloc[0]
    first = st.columns(4)
    for col, label, field in zip(first, ("Played", "Wins", "Draws", "Losses"),
                                  ("matches_played", "wins", "draws", "losses")):
        col.metric(label, int(row[field]))
    second = st.columns(4)
    second[0].metric("Goals for", int(row["goals_for"]))
    second[1].metric("Goals against", int(row["goals_against"]))
    second[2].metric("Points", int(row["points"]))
    second[3].metric("Win rate", f"{row['win_percentage']:.1f}%")

    form = queries.team_form(competition_id, season, int(team_id))
    if not form.empty:
        current = form.iloc[0]
        st.subheader("Recent form")
        st.write(f"**{current['recent_form']}** · {int(current['points_last_5'])} points in "
                 f"{int(current['recent_matches'])} recent matches · form score {current['form_score']:.2f}")

    split = queries.home_away(competition_id, season, int(team_id))
    if not split.empty:
        home_away = split.iloc[0]
        st.subheader("Home and away")
        left, right = st.columns(2)
        left.metric("Home record", f"{home_away['home_wins']}W {home_away['home_draws']}D {home_away['home_losses']}L")
        right.metric("Away record", f"{home_away['away_wins']}W {home_away['away_draws']}D {home_away['away_losses']}L")
        left.caption(f"Goals {home_away['home_goals_for']}–{home_away['home_goals_against']}")
        right.caption(f"Goals {home_away['away_goals_for']}–{home_away['away_goals_against']}")
        left.caption(f"Win rate {home_away['home_win_rate']:.1f}%" if home_away["home_matches"] else "No home matches")
        right.caption(f"Win rate {home_away['away_win_rate']:.1f}%" if home_away["away_matches"] else "No away matches")

    progression = queries.team_progression(competition_id, season, int(team_id))
    if not progression.empty:
        left, right = st.columns(2)
        with left:
            st.subheader("Goals progression")
            st.plotly_chart(px.line(progression, x="match_date", y="cumulative_goals", markers=True),
                            width='stretch')
        with right:
            st.subheader("Points progression")
            st.plotly_chart(px.line(progression, x="match_date", y="cumulative_points", markers=True),
                            width='stretch')
        st.subheader("Recent matches")
        recent = progression.tail(5).iloc[::-1]
        st.dataframe(recent[["match_date", "opponent_name", "venue_type", "result",
                             "goals_for", "goals_against", "points"]],
                     hide_index=True, width='stretch')


render()
