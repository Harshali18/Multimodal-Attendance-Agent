
from pathlib import Path
import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

CSV_FILES = [
    "tracking_data.csv",
    "attendance_report.csv",
    "engagement_scores.csv",
    "teaching_suggestions.csv",
    "student_analytics.csv",
]

JSON_FILES = [
    "multimodal_insights.json",
    "fused_multimodal_data.json",
    "engagement_summary.json",
    "student_analytics.json",
]

print("=" * 55)
print("MULTIMODAL ATTENDANCE AGENT - VALIDATION")
print("=" * 55)

for filename in CSV_FILES:
    path = BASE_DIR / filename
    if not path.exists():
        print(f"[MISSING] {filename}")
        continue

    try:
        df = pd.read_csv(path)
        print(f"[PASS] {filename}: {len(df)} rows, {len(df.columns)} columns")

        if df.empty:
            print(f"[WARNING] {filename} is empty")

        if df.isnull().all(axis=1).any():
            print(f"[WARNING] {filename} contains fully empty rows")

    except Exception as exc:
        print(f"[FAIL] {filename}: {exc}")

for filename in JSON_FILES:
    path = BASE_DIR / filename
    if not path.exists():
        print(f"[MISSING] {filename}")
        continue

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        print(f"[PASS] {filename}: valid JSON ({type(data).__name__})")
    except Exception as exc:
        print(f"[FAIL] {filename}: {exc}")

# Validate score range and timeline ordering.
engagement_path = BASE_DIR / "engagement_scores.csv"

if engagement_path.exists():
    try:
        df = pd.read_csv(engagement_path)
        required = {
            "window_start_seconds",
            "window_end_seconds",
            "engagement_score",
        }

        if not required.issubset(df.columns):
            print("[FAIL] Engagement CSV missing required columns")
        else:
            scores = pd.to_numeric(df["engagement_score"], errors="coerce")
            starts = pd.to_numeric(df["window_start_seconds"], errors="coerce")
            ends = pd.to_numeric(df["window_end_seconds"], errors="coerce")

            invalid_scores = scores.isna() | ~scores.between(0, 100)
            invalid_windows = starts.isna() | ends.isna() | (ends <= starts)

            print(
                f"[CHECK] Invalid or missing scores: "
                f"{int(invalid_scores.sum())}"
            )
            print(
                f"[CHECK] Invalid timeline windows: "
                f"{int(invalid_windows.sum())}"
            )

            if len(starts.dropna()) > 1:
                out_of_order = int((starts.diff().dropna() < 0).sum())
                print(f"[CHECK] Out-of-order windows: {out_of_order}")

    except Exception as exc:
        print(f"[FAIL] Engagement validation: {exc}")

print("=" * 55)
print("Validation checks completed. Review warnings and failures.")
print("Passing file checks do not prove real-world accuracy.")
print("=" * 55)
