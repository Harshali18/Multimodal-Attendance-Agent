
import os
import csv
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "fused_multimodal_data.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "engagement_scores.csv")
OUTPUT_JSON = os.path.join(BASE_DIR, "engagement_summary.json")

# Adjustable scoring weights (total = 100)
PRESENCE_WEIGHT = 40
MOVEMENT_WEIGHT = 15
AUDIO_WEIGHT = 25
ACTIVITY_CONTINUITY_WEIGHT = 20

# Adjustable thresholds
HIGH_RMS_THRESHOLD = 0.006
MOVEMENT_THRESHOLD = 20.0


def to_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def to_bool(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def main():
    if not os.path.isfile(INPUT_FILE):
        print("Fused data file nahi mili:", INPUT_FILE)
        print("Pehle multimodal_fusion.py run karo.")
        return

    with open(INPUT_FILE, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Fused data file empty hai.")
        return

    scores = []

    for row in rows:
        start = to_float(row.get("window_start_seconds"))
        end = to_float(row.get("window_end_seconds"), start + 1)

        visual_records = int(to_float(row.get("visual_tracking_records")))
        tracker_count = int(
            to_float(row.get("unique_tracker_ids_in_window"))
        )
        movement = to_float(row.get("movement_pixels_estimate"))
        rms = to_float(row.get("mean_rms_energy"))

        vision_available = to_bool(row.get("vision_data_available"))
        audio_available = to_bool(row.get("audio_data_available"))

        labels = [
            label.strip().lower()
            for label in row.get("audio_labels", "").split(";")
            if label.strip()
        ]

        # 1. Presence indicator: tracking was detected in this window.
        presence_score = 100.0 if vision_available and visual_records > 0 else 0.0

        # 2. Movement indicator: a modest movement signal, not attention.
        movement_score = (
            min(100.0, movement / MOVEMENT_THRESHOLD * 100)
            if vision_available else 0.0
        )

        # 3. Audio indicator: higher energy is only a sound-activity cue.
        if not audio_available:
            audio_score = 0.0
        elif "possible_speech_or_loud_audio" in labels:
            audio_score = 100.0
        elif rms >= HIGH_RMS_THRESHOLD:
            audio_score = 70.0
        elif rms > 0:
            audio_score = 35.0
        else:
            audio_score = 0.0

        # 4. Continuity indicator: whether visual tracking is present.
        continuity_score = 100.0 if vision_available and visual_records > 0 else 0.0

        # Reweight only the modalities actually available in this window.
        components = []
        if vision_available:
            components.extend([
                (presence_score, PRESENCE_WEIGHT),
                (movement_score, MOVEMENT_WEIGHT),
                (continuity_score, ACTIVITY_CONTINUITY_WEIGHT),
            ])

        if audio_available:
            components.append((audio_score, AUDIO_WEIGHT))

        available_weight = sum(weight for _, weight in components)

        score = (
            sum(value * weight for value, weight in components) / available_weight
            if available_weight else 0.0
        )

        if not vision_available and not audio_available:
            level = "insufficient_data"
        elif score >= 70:
            level = "higher_observed_activity"
        elif score >= 40:
            level = "moderate_observed_activity"
        else:
            level = "lower_observed_activity"

        notes = []
        if not vision_available:
            notes.append("No visual tracking in this window")
        if not audio_available:
            notes.append("No audio segment in this window")
        if movement_score > 0:
            notes.append("Bounding-box movement detected")
        if "possible_speech_or_loud_audio" in labels:
            notes.append("Higher audio energy; speech not verified")

        scores.append({
            "window_start_seconds": round(start, 3),
            "window_end_seconds": round(end, 3),
            "engagement_score": round(score, 2),
            "activity_level": level,
            "visual_presence_score": round(presence_score, 2),
            "movement_indicator_score": round(movement_score, 2),
            "audio_activity_score": round(audio_score, 2),
            "continuity_indicator_score": round(continuity_score, 2),
            "vision_data_available": vision_available,
            "audio_data_available": audio_available,
            "visual_tracking_records": visual_records,
            "tracker_count": tracker_count,
            "movement_pixels_estimate": round(movement, 3),
            "mean_rms_energy": round(rms, 6),
            "interpretation_notes": "; ".join(notes),
        })

    valid_scores = [
        item["engagement_score"]
        for item in scores
        if item["activity_level"] != "insufficient_data"
    ]

    average_score = (
        sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    )

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(scores[0].keys()))
        writer.writeheader()
        writer.writerows(scores)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scoring_method": "transparent_rule_based_heuristic",
        "score_range": "0-100",
        "total_windows": len(scores),
        "windows_with_sufficient_modality_data": len(valid_scores),
        "mean_observed_activity_score": round(average_score, 2),
        "higher_activity_windows": sum(
            item["activity_level"] == "higher_observed_activity"
            for item in scores
        ),
        "moderate_activity_windows": sum(
            item["activity_level"] == "moderate_observed_activity"
            for item in scores
        ),
        "lower_activity_windows": sum(
            item["activity_level"] == "lower_observed_activity"
            for item in scores
        ),
        "insufficient_data_windows": sum(
            item["activity_level"] == "insufficient_data"
            for item in scores
        ),
        "weights": {
            "presence": PRESENCE_WEIGHT,
            "movement": MOVEMENT_WEIGHT,
            "audio": AUDIO_WEIGHT,
            "continuity": ACTIVITY_CONTINUITY_WEIGHT,
        },
        "thresholds": {
            "high_rms": HIGH_RMS_THRESHOLD,
            "movement_pixels": MOVEMENT_THRESHOLD,
        },
        "limitations": [
            "Scores are heuristic activity indicators, not validated engagement measurements.",
            "Movement does not necessarily indicate attention.",
            "Audio energy does not prove speech or interaction.",
            "Vision and audio timestamps are not verified on a shared clock.",
            "Tracker IDs are not verified student identities.",
            "Missing modality data is excluded from weighting, not treated as proof of disengagement.",
        ],
        "temporal_profile": scores,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    print("\nEngagement scoring complete!")
    print("Time windows scored:", len(scores))
    print("Windows with modality data:", len(valid_scores))
    print("Mean observed activity score:", round(average_score, 2), "/ 100")
    print("CSV report:", OUTPUT_CSV)
    print("JSON summary:", OUTPUT_JSON)
    print("\nNote: Scores heuristic hain, verified student engagement nahi.")


if __name__ == "__main__":
    main()
