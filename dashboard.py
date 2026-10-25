
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Multimodal Attendance Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Multimodal Attendance Agent")
st.caption("Session analytics, attendance estimates and reflective insights")

st.info(
    "Important: These outputs use heuristic estimates. "
    "Tracker IDs are not verified student identities, and session "
    "activity scores are not individual engagement measurements."
)


def load_csv(filename):
    path = BASE_DIR / filename
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except (ValueError, pd.errors.ParserError, OSError) as exc:
        st.warning(f"Could not read {filename}: {exc}")
        return None


def load_json(filename):
    path = BASE_DIR / filename
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        st.warning(f"Could not read {filename}: {exc}")
        return None


attendance = load_csv("attendance_report.csv")
engagement = load_csv("engagement_scores.csv")
suggestions = load_csv("teaching_suggestions.csv")
analytics = load_json("student_analytics.json")

if analytics is None:
    st.warning(
        "student_analytics.json not found. Run student_analytics.py first."
    )

# Overview metrics
m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Tracked IDs",
    len(attendance) if attendance is not None else "N/A",
)
m2.metric(
    "Timeline windows",
    len(engagement) if engagement is not None else "N/A",
)
m3.metric(
    "Instructor suggestions",
    len(suggestions) if suggestions is not None else "N/A",
)

summary = (
    analytics.get("session_level_activity_summary", {})
    if analytics else {}
)
mean_score = summary.get("mean_session_activity_score")
m4.metric(
    "Mean session activity",
    f"{mean_score:.2f}/100" if isinstance(mean_score, (int, float)) else "N/A",
)

tab1, tab2, tab3, tab4 = st.tabs([
    "Attendance",
    "Engagement Timeline",
    "Instructor Suggestions",
    "Student Analytics",
])

with tab1:
    st.subheader("Estimated Attendance Records")

    if attendance is not None:
        st.caption("Tracker IDs are temporary identifiers, not confirmed names.")
        st.dataframe(attendance, use_container_width=True, hide_index=True)

        if {"participant_id", "cumulative_presence_seconds"}.issubset(
            attendance.columns
        ):
            chart_data = attendance.copy()
            chart_data["cumulative_presence_seconds"] = pd.to_numeric(
                chart_data["cumulative_presence_seconds"],
                errors="coerce",
            )
            chart_data = chart_data.dropna(
                subset=["cumulative_presence_seconds"]
            )

            if not chart_data.empty:
                chart_data["participant_id"] = (
                    chart_data["participant_id"].astype(str)
                )
                chart_data = chart_data.sort_values(
                    "cumulative_presence_seconds", ascending=False
                )

                fig = px.bar(
                    chart_data,
                    x="participant_id",
                    y="cumulative_presence_seconds",
                    title="Estimated observed presence by tracker ID",
                    labels={
                        "participant_id": "Tracker ID",
                        "cumulative_presence_seconds": "Seconds",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("attendance_report.csv not found.")

with tab2:
    st.subheader("Session Activity Timeline")

    if engagement is not None:
        required = {
            "window_start_seconds",
            "engagement_score",
        }

        if required.issubset(engagement.columns):
            timeline = engagement.copy()
            timeline["window_start_seconds"] = pd.to_numeric(
                timeline["window_start_seconds"], errors="coerce"
            )
            timeline["engagement_score"] = pd.to_numeric(
                timeline["engagement_score"], errors="coerce"
            )
            timeline = timeline.dropna(
                subset=["window_start_seconds", "engagement_score"]
            ).sort_values("window_start_seconds")

            fig = px.line(
                timeline,
                x="window_start_seconds",
                y="engagement_score",
                markers=True,
                title="Heuristic session activity score over time",
                labels={
                    "window_start_seconds": "Time (seconds)",
                    "engagement_score": "Activity score",
                },
            )
            fig.update_yaxes(range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

            if "activity_level" in timeline.columns:
                st.caption("Activity labels from the scoring script:")
                st.dataframe(
                    timeline[
                        ["window_start_seconds", "engagement_score",
                         "activity_level"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            with st.expander("View all engagement data"):
                st.dataframe(
                    engagement, use_container_width=True, hide_index=True
                )
        else:
            st.warning("Engagement CSV is missing required columns.")
    else:
        st.warning("engagement_scores.csv not found.")

with tab3:
    st.subheader("Instructor Suggestions")

    if suggestions is not None:
        st.dataframe(suggestions, use_container_width=True, hide_index=True)

        # Show a category chart if the CSV contains a category/type column.
        category_col = next(
            (
                col for col in ["suggestion_type", "category", "trigger_type"]
                if col in suggestions.columns
            ),
            None,
        )

        if category_col:
            counts = (
                suggestions[category_col]
                .fillna("Unspecified")
                .astype(str)
                .value_counts()
                .rename_axis("Suggestion type")
                .reset_index(name="Count")
            )
            fig = px.bar(
                counts,
                x="Suggestion type",
                y="Count",
                title="Suggestion categories",
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("How to interpret suggestions"):
            st.write(
                "Suggestions are rule-based prompts for instructor review. "
                "They do not establish why an activity pattern occurred "
                "or prove that a teaching change is necessary."
            )
    else:
        st.warning("teaching_suggestions.csv not found.")

with tab4:
    st.subheader("Reflective Student Session Analytics")

    if analytics is not None:
        individuals = analytics.get("individual_summaries", [])
        session_timeline = analytics.get("session_activity_timeline", [])

        st.write(
            "Individual summaries describe estimated presence. "
            "The activity timeline describes the session as a whole."
        )

        if individuals:
            student_df = pd.DataFrame(individuals)
            st.dataframe(
                student_df,
                use_container_width=True,
                hide_index=True,
            )

            if "participant_id" in student_df.columns:
                ids = student_df["participant_id"].astype(str).tolist()
                selected_id = st.selectbox(
                    "Explore a tracker summary",
                    ids,
                )
                selected = student_df[
                    student_df["participant_id"].astype(str) == selected_id
                ]

                if not selected.empty:
                    record = selected.iloc[0].to_dict()
                    st.write(
                        record.get("presence_summary", "Presence summary unavailable.")
                    )
                    st.write(
                        record.get(
                            "reflection_prompt",
                            "Reflect on your participation and choose one small goal.",
                        )
                    )
                    st.caption(
                        record.get("interpretation_note", "")
                    )

        if session_timeline:
            st.markdown("**Session-level activity summary**")
            st.json(summary)

            timeline_df = pd.DataFrame(session_timeline)
            if {
                "start_seconds",
                "session_activity_score",
            }.issubset(timeline_df.columns):
                fig = px.line(
                    timeline_df,
                    x="start_seconds",
                    y="session_activity_score",
                    title="Reflective session activity timeline",
                    labels={
                        "start_seconds": "Time (seconds)",
                        "session_activity_score": "Activity score",
                    },
                )
                fig.update_yaxes(range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)

        with st.expander("Privacy and interpretation"):
            st.write(
                analytics.get(
                    "privacy_and_interpretation",
                    "No grades or peer rankings are generated.",
                )
            )
    else:
        st.warning("Generate student_analytics.json to view this section.")

st.divider()
st.caption(
    "Optional visualization layer • Local files only • "
    "Refresh the page after regenerating reports"
)
