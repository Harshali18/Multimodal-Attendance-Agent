
import os
import csv
import json
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VISION_FILE = os.path.join(BASE_DIR, "tracking_data.csv")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance_report.csv")
AUDIO_FILE = os.path.join(BASE_DIR, "segment_audio_insights.csv")

OUTPUT_JSON = os.path.join(BASE_DIR, "fused_multimodal_data.json")
OUTPUT_CSV = os.path.join(BASE_DIR, "fused_multimodal_data.csv")

# Fusion window: 1 second
WINDOW_SECONDS = 1.0


def read_csv(path):
    if not os.path.isfile(path):
        print("File nahi mili:", os.path.basename(path))
        return []

    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def to_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_timestamp(value):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def main():
    vision = read_csv(VISION_FILE)
    attendance = read_csv(ATTENDANCE_FILE)
    audio = read_csv(AUDIO_FILE)

    if not vision:
        print("Vision data missing hai.")
        return

    if not audio:
        print("Audio data missing hai.")
        return

    # Attendance lookup by tracker ID
    attendance_lookup = {
        row.get("participant_id", "").strip(): row
        for row in attendance
        if row.get("participant_id", "").strip()
    }

    # Vision timestamps are currently processing timestamps.
    # Convert them to relative seconds from the first valid timestamp.
    parsed_vision = []

    for row in vision:
        timestamp = parse_timestamp(row.get("timestamp", ""))
        if timestamp is None:
            continue

        parsed_vision.append((timestamp, row))

    if not parsed_vision:
        print("Vision timestamps parse nahi ho paaye.")
        return

    vision_origin = min(item[0] for item in parsed_vision)

    visual_windows = defaultdict(lambda: {
        "tracker_ids": set(),
        "records": 0,
        "movement_pixels": 0.0,
        "previous_positions": {}
    })

    for timestamp, row in parsed_vision:
        relative_seconds = (timestamp - vision_origin).total_seconds()
        window = int(relative_seconds // WINDOW_SECONDS)

        participant_id = row.get("participant_id", "").strip()
        x = to_float(row.get("x"))
        y = to_float(row.get("y"))

        bucket = visual_windows[window]
        bucket["records"] += 1

        if participant_id:
            bucket["tracker_ids"].add(participant_id)

            previous = bucket["previous_positions"].get(participant_id)
            if previous is not None:
                dx = x - previous[0]
                dy = y - previous[1]
                bucket["movement_pixels"] += (dx * dx + dy * dy) ** 0.5

            bucket["previous_positions"][participant_id] = (x, y)

    # Audio segment offsets are relative to each audio recording.
    # Without a shared start time, do NOT assume these align exactly
    # with the vision clock.
    audio_windows = defaultdict(list)

    for row in audio:
        start = to_float(row.get("start_seconds"))
        end = to_float(row.get("end_seconds"), start)
        window = int(start // WINDOW_SECONDS)

        audio_windows[window].append({
            "start_seconds": start,
            "end_seconds": end,
            "audio_label": row.get("audio_label", "unknown"),
            "rms_energy": to_float(row.get("rms_energy")),
            "peak_amplitude": to_float(row.get("peak_amplitude"))
        })

    all_windows = sorted(set(visual_windows) | set(audio_windows))
    fused_rows = []

    for window in all_windows:
        visual = visual_windows[window]
        audio_segments = audio_windows[window]

        labels = [item["audio_label"] for item in audio_segments]
        mean_rms = (
            sum(item["rms_energy"] for item in audio_segments)
            / len(audio_segments)
            if audio_segments else 0.0
        )

        fused_rows.append({
            "window_start_seconds": round(window * WINDOW_SECONDS, 3),
            "window_end_seconds": round((window + 1) * WINDOW_SECONDS, 3),
            "visual_tracking_records": visual["records"],
            "unique_tracker_ids_in_window": len(visual["tracker_ids"]),
            "tracker_ids": ";".join(sorted(visual["tracker_ids"])),
            "movement_pixels_estimate": round(
                visual["movement_pixels"], 3
            ),
            "audio_segments": len(audio_segments),
            "audio_labels": ";".join(labels),
            "mean_rms_energy": round(mean_rms, 6),
            "audio_data_available": bool(audio_segments),
            "vision_data_available": visual["records"] > 0,
            "synchronization_status": "relative_time_only_unverified"
        })

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "fusion_method": "timestamp_window_aggregation",
        "window_seconds": WINDOW_SECONDS,
        "vision_records_read": len(vision),
        "vision_records_with_valid_timestamps": len(parsed_vision),
        "attendance_records_read": len(attendance),
        "audio_segments_read": len(audio),
        "attendance_lookup_ids": len(attendance_lookup),
        "fusion_windows": fused_rows,
        "limitations": [
            "Vision timestamps are processing wall-clock times.",
            "Audio offsets start from each recording, not a shared session clock.",
            "Cross-modal alignment is unverified until both modules share a clock.",
            "Movement is an approximate bounding-box displacement, not engagement.",
            "Audio energy labels do not confirm speech or interaction.",
            "Tracker IDs do not confirm real student identities."
        ]
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as file:
        if fused_rows:
            writer = csv.DictWriter(
                file, fieldnames=list(fused_rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(fused_rows)

    print("\nMultimodal fusion complete!")
    print("Vision records:", len(vision))
    print("Valid vision timestamps:", len(parsed_vision))
    print("Audio segments:", len(audio))
    print("Fusion windows:", len(fused_rows))
    print("JSON output:", OUTPUT_JSON)
    print("CSV output:", OUTPUT_CSV)
    print(
        "\nNote: timestamp alignment abhi relative hai; "
        "synchronized engagement ka verified proof nahi."
    )


if __name__ == "__main__":
    main()
