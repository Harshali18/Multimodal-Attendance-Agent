
import csv
import os
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "tracking_data.csv")
REPORT_PATH = os.path.join(BASE_DIR, "attendance_report.csv")

# Settings: in values ko zaroorat ke hisaab se badal sakte ho
MIN_PRESENCE_SECONDS = 60
MAX_GAP_SECONDS = 2.0

if not os.path.isfile(CSV_PATH):
    print("tracking_data.csv file nahi mili!")
    raise SystemExit(1)

# Har participant ke unique timestamps collect karo
participant_times = defaultdict(set)

with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    required = {"participant_id", "timestamp"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        print("CSV mein participant_id aur timestamp columns hone chahiye.")
        raise SystemExit(1)

    for row in reader:
        try:
            participant_id = row["participant_id"].strip()
            timestamp = datetime.fromisoformat(row["timestamp"])

            if participant_id:
                participant_times[participant_id].add(timestamp)
        except (ValueError, TypeError, KeyError, AttributeError):
            continue

if not participant_times:
    print("CSV mein valid tracking records nahi mile.")
    raise SystemExit(0)

report_rows = []

for participant_id, timestamps in sorted(participant_times.items()):
    times = sorted(timestamps)

    first_seen = times[0]
    last_seen = times[-1]
    cumulative_presence = 0.0
    current_session = 0.0
    longest_session = 0.0

    for previous, current in zip(times, times[1:]):
        gap = (current - previous).total_seconds()

        # Sirf chhote gaps ko visible presence ka estimate maano
        if 0 < gap <= MAX_GAP_SECONDS:
            cumulative_presence += gap
            current_session += gap
        else:
            longest_session = max(longest_session, current_session)
            current_session = 0.0

    longest_session = max(longest_session, current_session)

    status = (
        "Present"
        if cumulative_presence >= MIN_PRESENCE_SECONDS
        else "Absent"
    )

    report_rows.append([
        participant_id,
        first_seen.isoformat(),
        last_seen.isoformat(),
        round(cumulative_presence, 2),
        round(longest_session, 2),
        len(times),
        MIN_PRESENCE_SECONDS,
        status
    ])

with open(REPORT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "participant_id",
        "first_seen",
        "last_seen",
        "cumulative_presence_seconds",
        "longest_session_seconds",
        "unique_timestamps",
        "minimum_required_seconds",
        "attendance_status"
    ])
    writer.writerows(report_rows)

present_count = sum(row[-1] == "Present" for row in report_rows)

print("Attendance report ban gayi:", REPORT_PATH)
print("Tracked participant IDs:", len(report_rows))
print("Present:", present_count)
print("Below threshold:", len(report_rows) - present_count)
print("Minimum presence threshold:", MIN_PRESENCE_SECONDS, "seconds")
print("Note: yeh estimated presence hai, verified identity ya continuous attendance ka proof nahi.")
