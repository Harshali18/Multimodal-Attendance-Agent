
import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

ATTENDANCE_FILE = BASE_DIR / "attendance_report.csv"
ENGAGEMENT_FILE = BASE_DIR / "engagement_scores.csv"

OUTPUT_CSV = BASE_DIR / "student_analytics.csv"
OUTPUT_JSON = BASE_DIR / "student_analytics.json"

LOW_THRESHOLD = 40
HIGH_THRESHOLD = 70


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.name}")
    return pd.read_csv(path)


def main():
    attendance = read_csv(ATTENDANCE_FILE)
    engagement = read_csv(ENGAGEMENT_FILE)

    required_attendance = {
        "participant_id",
        "cumulative_presence_seconds",
        "attendance_status",
    }
    required_engagement = {
        "window_start_seconds",
        "window_end_seconds",
        "engagement_score",
        "activity_level",
    }

    if not required_attendance.issubset(attendance.columns):
        raise ValueError("Attendance CSV columns are incomplete.")

    if not required_engagement.issubset(engagement.columns):
        raise ValueError("Engagement CSV columns are incomplete.")

    attendance["participant_id"] = attendance["participant_id"].astype(str)

    for col in [
        "cumulative_presence_seconds",
        "window_start_seconds",
        "window_end_seconds",
        "engagement_score",
    ]:
        source = attendance if col in attendance.columns else engagement
        if col in source.columns:
            source[col] = pd.to_numeric(source[col], errors="coerce")

    engagement = engagement.dropna(
        subset=["window_start_seconds", "window_end_seconds",
                "engagement_score"]
    ).sort_values("window_start_seconds")

    engagement["engagement_score"] = engagement[
        "engagement_score"
    ].clip(0, 100)

    timeline = []
    for _, row in engagement.iterrows():
        score = float(row["engagement_score"])
        if score >= HIGH_THRESHOLD:
            level = "higher_observed_session_activity"
        elif score < LOW_THRESHOLD:
            level = "lower_observed_session_activity"
        else:
            level = "moderate_observed_session_activity"

        timeline.append({
            "start_seconds": float(row["window_start_seconds"]),
            "end_seconds": float(row["window_end_seconds"]),
            "session_activity_score": round(score, 2),
            "descriptive_level": level,
            "activity_level_from_source": str(row["activity_level"]),
        })

    session_scores = engagement["engagement_score"].dropna()
    if len(session_scores):
        session_summary = {
            "windows_analyzed": int(len(session_scores)),
            "mean_session_activity_score": round(
                float(session_scores.mean()), 2
            ),
            "higher_activity_windows": int(
                (session_scores >= HIGH_THRESHOLD).sum()
            ),
            "lower_activity_windows": int(
                (session_scores < LOW_THRESHOLD).sum()
            ),
            "score_variation": round(
                float(session_scores.std(ddof=0)), 2
            ),
        }
    else:
        session_summary = {
            "windows_analyzed": 0,
            "mean_session_activity_score": None,
            "higher_activity_windows": 0,
            "lower_activity_windows": 0,
            "score_variation": None,
        }

    student_reports = []

    for _, row in attendance.iterrows():
        duration = row["cumulative_presence_seconds"]
        duration = float(duration) if pd.notna(duration) else None

        if duration is None:
            presence_text = "Estimated presence duration unavailable."
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            presence_text = f"Estimated observed presence: {minutes} min {seconds} sec."

        student_reports.append({
            "participant_id": str(row["participant_id"]),
            "estimated_presence_seconds": duration,
            "attendance_status_from_existing_report": str(
                row["attendance_status"]
            ),
            "personal_engagement_score": None,
            "session_activity_context": (
                "See the separate session-level timeline; it is not "
                "a personal engagement measurement."
            ),
            "presence_summary": presence_text,
            "reflection_prompt": (
                "Reflect on your experience of the session and choose "
                "one small participation goal for next time."
            ),
            "interpretation_note": (
                "Tracker IDs are not verified student identities. "
                "Presence is an estimate, not proof of attendance."
            ),
        })

    output = {
        "report_type": "reflective_student_session_analytics",
        "individual_summaries": student_reports,
        "session_level_activity_summary": session_summary,
        "session_activity_timeline": timeline,
        "privacy_and_interpretation": (
            "No grades or peer rankings are produced. Session-level "
            "activity scores are not assigned to individual students. "
            "Timestamps and tracker identities are not independently verified."
        ),
    }

    pd.DataFrame(student_reports).to_csv(OUTPUT_CSV, index=False)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print("Student analytics generated successfully!")
    print(f"Individual summaries: {len(student_reports)}")
    print(f"Session timeline windows: {len(timeline)}")
    print(f"CSV report: {OUTPUT_CSV.name}")
    print(f"JSON report: {OUTPUT_JSON.name}")
    print("Personal engagement scores: not assigned (no per-student data).")


if __name__ == "__main__":
    main()
