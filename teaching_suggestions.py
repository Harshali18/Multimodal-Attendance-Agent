
import os
import csv
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "engagement_scores.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "teaching_suggestions.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "teaching_suggestions.json")

# Adjustable thresholds
LOW_SCORE_THRESHOLD = 40
HIGH_SCORE_THRESHOLD = 70
SCORE_DROP_THRESHOLD = 20
SUSTAINED_WINDOWS = 3
HIGH_AUDIO_RMS_THRESHOLD = 0.015


def read_csv(path):
    if not os.path.isfile(path):
        print("Required file nahi mili:", os.path.basename(path))
        return []

    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def to_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def to_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def main():
    rows = read_csv(INPUT_FILE)

    if not rows:
        print("Engagement scores missing hain. Pehle engagement_scoring.py run karo.")
        return

    rows.sort(key=lambda row: to_float(row.get("window_start_seconds")))

    suggestions = []
    events = []

    def add_suggestion(category, priority, start, end, evidence, message):
        suggestions.append({
            "category": category,
            "priority": priority,
            "start_seconds": round(start, 2),
            "end_seconds": round(end, 2),
            "evidence": evidence,
            "recommendation": message,
            "status": "suggestion_for_instructor_review"
        })

    # Find consecutive low-score windows
    low_run = []

    def finish_low_run(run):
        if len(run) >= SUSTAINED_WINDOWS:
            start = to_float(run[0].get("window_start_seconds"))
            end = to_float(run[-1].get("window_end_seconds"), start)
            add_suggestion(
                "sustained_low_activity",
                "medium",
                start,
                end,
                f"{len(run)} consecutive windows below {LOW_SCORE_THRESHOLD}",
                "Consider a short interactive question, discussion, or activity. "
                "Check classroom context before changing the lesson."
            )

    previous_score = None
    previous_row = None
    peak_windows = []

    for row in rows:
        start = to_float(row.get("window_start_seconds"))
        end = to_float(row.get("window_end_seconds"), start + 1)
        score = to_float(row.get("engagement_score"))
        level = row.get("activity_level", "")
        audio_available = to_bool(row.get("audio_data_available"))
        rms = to_float(row.get("mean_rms_energy"))
        labels = row.get("interpretation_notes", "").lower()

        if level == "insufficient_data":
            finish_low_run(low_run)
            low_run = []
            previous_score = None
            previous_row = None
            continue

        if score < LOW_SCORE_THRESHOLD:
            low_run.append(row)
        else:
            finish_low_run(low_run)
            low_run = []

        # Flag a noticeable score drop between adjacent available windows
        if previous_score is not None:
            drop = previous_score - score
            if drop >= SCORE_DROP_THRESHOLD:
                add_suggestion(
                    "activity_drop",
                    "medium",
                    start,
                    end,
                    f"Score decreased by {drop:.1f} points between adjacent windows",
                    "Consider checking whether the topic, pace, or activity needs "
                    "a transition, recap, or comprehension question."
                )

        if score >= HIGH_SCORE_THRESHOLD:
            peak_windows.append(row)

        # Audio conditions are only evaluated where audio exists
        if audio_available and (
            rms >= HIGH_AUDIO_RMS_THRESHOLD
            or "higher audio energy" in labels
        ):
            add_suggestion(
                "high_audio_energy",
                "low",
                start,
                end,
                f"Audio RMS energy: {rms:.6f}",
                "Check whether the sound reflects group discussion, a useful "
                "interactive activity, or unwanted classroom noise before acting."
            )

        previous_score = score
        previous_row = row

    finish_low_run(low_run)

    # Summarize high-scoring intervals rather than creating a suggestion per window
    if peak_windows:
        peak_start = to_float(peak_windows[0].get("window_start_seconds"))
        peak_end = to_float(peak_windows[-1].get("window_end_seconds"), peak_start)

        add_suggestion(
            "higher_activity_periods",
            "low",
            peak_start,
            peak_end,
            f"{len(peak_windows)} windows scored at least {HIGH_SCORE_THRESHOLD}",
            "Review what was happening during these higher-scoring periods. "
            "If supported by lesson notes, consider reusing the teaching approach."
        )

    # Remove duplicate suggestions with identical category and time range
    unique = []
    seen = set()

    for item in suggestions:
        key = (
            item["category"],
            item["start_seconds"],
            item["end_seconds"]
        )
        if key not in seen:
            seen.add(key)
            unique.append(item)

    for index, item in enumerate(unique, start=1):
        item["suggestion_id"] = f"TS-{index:03d}"

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": os.path.basename(INPUT_FILE),
        "windows_analyzed": len(rows),
        "suggestions_generated": len(unique),
        "rule_thresholds": {
            "low_score": LOW_SCORE_THRESHOLD,
            "high_score": HIGH_SCORE_THRESHOLD,
            "score_drop": SCORE_DROP_THRESHOLD,
            "sustained_windows": SUSTAINED_WINDOWS,
            "high_audio_rms": HIGH_AUDIO_RMS_THRESHOLD
        },
        "suggestions": unique,
        "limitations": [
            "Engagement scores are heuristic estimates, not validated measurements.",
            "High movement or audio energy does not necessarily mean engagement or noise.",
            "Audio and vision timestamps are not verified on a shared clock.",
            "High-scoring periods do not prove a particular teaching method caused the score.",
            "Instructor review and classroom context are required before acting."
        ]
    }

    fields = [
        "suggestion_id",
        "category",
        "priority",
        "start_seconds",
        "end_seconds",
        "evidence",
        "recommendation",
        "status"
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(unique)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    print("\nTeaching suggestions generated!")
    print("Windows analyzed:", len(rows))
    print("Suggestions generated:", len(unique))

    if unique:
        print("\nSuggestion categories:")
        for category in sorted({item["category"] for item in unique}):
            count = sum(item["category"] == category for item in unique)
            print(f"- {category}: {count}")
    else:
        print("Current thresholds par koi suggestion trigger nahi hui.")
        print("Ye valid result hai; thresholds ko bina evidence ke change na karein.")

    print("\nCSV report:", OUTPUT_CSV)
    print("JSON report:", OUTPUT_JSON)
    print("\nNote: Suggestions instructor review ke liye hain, automatic decisions nahi.")


if __name__ == "__main__":
    main()
