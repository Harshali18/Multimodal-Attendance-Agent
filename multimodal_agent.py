
import os
import csv
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VISION_FILE = os.path.join(BASE_DIR, "tracking_data.csv")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance_report.csv")
AUDIO_FILE = os.path.join(BASE_DIR, "segment_audio_insights.csv")
AUDIO_SUMMARY_FILE = os.path.join(BASE_DIR, "session_audio_summary.csv")

OUTPUT_JSON = os.path.join(BASE_DIR, "multimodal_insights.json")
OUTPUT_CSV = os.path.join(BASE_DIR, "multimodal_insights.csv")


def read_csv(filepath):
    if not os.path.isfile(filepath):
        print("Required file nahi mili:", os.path.basename(filepath))
        return []

    with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def number(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def main():
    vision = read_csv(VISION_FILE)
    attendance = read_csv(ATTENDANCE_FILE)
    audio = read_csv(AUDIO_FILE)
    audio_summary_rows = read_csv(AUDIO_SUMMARY_FILE)

    if not vision or not audio:
        print("Vision ya audio data missing hai. Pehle modules run karo.")
        return

    # Vision summary
    participant_ids = {
        row.get("participant_id", "").strip()
        for row in vision
        if row.get("participant_id", "").strip()
    }

    tracked_frames = len(vision)
    unique_tracked_ids = len(participant_ids)

    # Attendance summary
    present_count = sum(
        row.get("attendance_status", "").strip().lower() == "present"
        for row in attendance
    )

    attendance_count = len(attendance)

    # Audio summary
    audio_labels = [row.get("audio_label", "") for row in audio]
    total_audio_segments = len(audio_labels)

    quiet_count = sum(
        label == "silence_or_very_quiet" for label in audio_labels
    )
    noise_count = sum(
        label == "background_noise_or_quiet_audio" for label in audio_labels
    )
    possible_speech_count = sum(
        label == "possible_speech_or_loud_audio" for label in audio_labels
    )

    possible_speech_ratio = (
        possible_speech_count / total_audio_segments
        if total_audio_segments else 0
    )

    mean_rms = (
        sum(number(row.get("rms_energy")) for row in audio)
        / total_audio_segments
        if total_audio_segments else 0
    )

    # Explainable rule-based reasoning
    rules_triggered = []
    insights = []

    if unique_tracked_ids > 0:
        rules_triggered.append("VISION_TRACKING_AVAILABLE")
        insights.append(
            f"Vision module ne {unique_tracked_ids} unique tracker IDs "
            f"aur {tracked_frames} tracking records report kiye."
        )

    if attendance_count > 0:
        rules_triggered.append("ATTENDANCE_REPORT_AVAILABLE")
        insights.append(
            f"Attendance report mein {present_count} participants present "
            f"aur {attendance_count} total tracked IDs listed hain."
        )

    if quiet_count > 0:
        rules_triggered.append("LOW_AUDIO_ENERGY_SEGMENTS")
        insights.append(
            f"{quiet_count} audio segments quiet ya near-silent classify hue."
        )

    if noise_count > 0:
        rules_triggered.append("NOISE_OR_QUIET_AUDIO_SEGMENTS")
        insights.append(
            f"{noise_count} segments background noise ya quiet audio "
            "ke roop mein classify hue."
        )

    if possible_speech_count > 0:
        rules_triggered.append("POSSIBLE_SPEECH_OR_LOUD_AUDIO")
        insights.append(
            f"{possible_speech_count} segments mein higher audio energy thi; "
            "ye speech ya loud sound ho sakta hai."
        )

    if possible_speech_ratio >= 0.5:
        session_context = "frequent_high_audio_energy"
        insights.append(
            "Kam se kam aadhe analyzed segments mein higher audio energy thi."
        )
    elif quiet_count / total_audio_segments >= 0.5:
        session_context = "mostly_quiet_audio"
        insights.append(
            "Kam se kam aadhe analyzed segments quiet ya near-silent the."
        )
    else:
        session_context = "mixed_audio_activity"
        insights.append(
            "Audio segments mein mixed energy levels mile."
        )

    if not attendance:
        insights.append(
            "Attendance data unavailable hai; attendance-based reasoning "
            "nahi ki gayi."
        )

    insights.append(
        "Tracker IDs verified student identities nahi hain. "
        "Audio energy actual speech ya engagement ka proof nahi hai."
    )

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "agent_type": "rule_based_multimodal_agent",
        "session_context": session_context,
        "vision": {
            "tracking_records": tracked_frames,
            "unique_tracker_ids": unique_tracked_ids,
            "note": "Tracker IDs distinct verified students ki guarantee nahi."
        },
        "attendance": {
            "participants_listed": attendance_count,
            "marked_present": present_count
        },
        "audio": {
            "segments_analyzed": total_audio_segments,
            "quiet_segments": quiet_count,
            "noise_or_quiet_segments": noise_count,
            "possible_speech_or_loud_segments": possible_speech_count,
            "possible_speech_or_loud_ratio": round(possible_speech_ratio, 3),
            "mean_rms_energy": round(mean_rms, 6)
        },
        "rules_triggered": rules_triggered,
        "insights": insights,
        "limitations": [
            "Audio and vision timestamps are not synchronized.",
            "Energy-based labels do not verify speech.",
            "Face presence alone does not establish attention or engagement.",
            "Session context is an interpretable estimate, not a validated score."
        ]
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    # CSV summary: one row per session
    flat_result = {
        "generated_at": result["generated_at"],
        "session_context": session_context,
        "tracking_records": tracked_frames,
        "unique_tracker_ids": unique_tracked_ids,
        "participants_listed": attendance_count,
        "marked_present": present_count,
        "audio_segments": total_audio_segments,
        "quiet_segments": quiet_count,
        "noise_or_quiet_segments": noise_count,
        "possible_speech_or_loud_segments": possible_speech_count,
        "possible_speech_or_loud_ratio": round(possible_speech_ratio, 3),
        "mean_rms_energy": round(mean_rms, 6),
        "rules_triggered": "; ".join(rules_triggered),
        "insights": " | ".join(insights)
    }

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_result.keys()))
        writer.writeheader()
        writer.writerow(flat_result)

    print("\nMultimodal Agent run complete!")
    print("Session context:", session_context)
    print("Tracking records:", tracked_frames)
    print("Unique tracker IDs:", unique_tracked_ids)
    print("Attendance present:", present_count, "/", attendance_count)
    print("Audio segments:", total_audio_segments)
    print("\nRules triggered:")
    for rule in rules_triggered:
        print("-", rule)

    print("\nGenerated files:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)
    print("\nInsights:")
    for insight in insights:
        print("-", insight)


if __name__ == "__main__":
    main()
