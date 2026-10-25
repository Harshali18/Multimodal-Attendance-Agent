
import os
import csv
import glob
import soundfile as sf
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEGMENTS_DIR = os.path.join(BASE_DIR, "audio_segments")

SEGMENT_REPORT = os.path.join(BASE_DIR, "segment_audio_insights.csv")
SESSION_REPORT = os.path.join(BASE_DIR, "session_audio_summary.csv")

# Basic starting thresholds; actual microphone ke hisaab se adjust ho sakte hain.
SILENCE_RMS = 0.001
NOISE_RMS = 0.006

FRAME_MS = 20


def analyze_segment(filepath):
    audio, sample_rate = sf.read(filepath, dtype="float32")

    # Stereo ho to mono mein convert karo
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    if len(audio) == 0:
        return None

    duration = len(audio) / sample_rate
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio ** 2)))

    # Short-time energy: 20 ms frames
    frame_size = max(1, int(sample_rate * FRAME_MS / 1000))
    frame_rms = []

    for start in range(0, len(audio), frame_size):
        frame = audio[start:start + frame_size]
        if len(frame):
            frame_rms.append(
                float(np.sqrt(np.mean(frame ** 2)))
            )

    frame_rms = np.array(frame_rms, dtype=np.float32)

    # Kitne frames mein audio level silence threshold se upar hai?
    if len(frame_rms):
        active_ratio = float(np.mean(frame_rms >= SILENCE_RMS))
        mean_frame_rms = float(np.mean(frame_rms))
        max_frame_rms = float(np.max(frame_rms))
    else:
        active_ratio = 0.0
        mean_frame_rms = 0.0
        max_frame_rms = 0.0

    # Zero-crossing rate: signal kitni baar zero cross karta hai
    zero_crossing_rate = float(
        np.mean(np.abs(np.diff(np.signbit(audio))))
    ) if len(audio) > 1 else 0.0

    if rms < SILENCE_RMS:
        label = "silence_or_very_quiet"
    elif rms < NOISE_RMS:
        label = "background_noise_or_quiet_audio"
    else:
        label = "possible_speech_or_loud_audio"

    return {
        "filename": os.path.basename(filepath),
        "sample_rate": sample_rate,
        "duration_seconds": round(duration, 3),
        "peak_amplitude": round(peak, 6),
        "rms_energy": round(rms, 6),
        "mean_frame_rms": round(mean_frame_rms, 6),
        "max_frame_rms": round(max_frame_rms, 6),
        "active_frame_ratio": round(active_ratio, 4),
        "zero_crossing_rate": round(zero_crossing_rate, 4),
        "audio_label": label,
    }


def main():
    files = sorted(glob.glob(os.path.join(SEGMENTS_DIR, "*.wav")))

    if not files:
        print("Koi WAV segment nahi mila:", SEGMENTS_DIR)
        print("Pehle audio_processing.py run karo.")
        return

    results = []

    for filepath in files:
        try:
            result = analyze_segment(filepath)
            if result:
                results.append(result)
        except Exception as error:
            print("File process nahi hui:", os.path.basename(filepath), error)

    if not results:
        print("Koi audio segment successfully analyze nahi hua.")
        return

    # Har segment ka detailed report
    columns = list(results[0].keys())

    with open(SEGMENT_REPORT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    # Session-level summary
    labels = [
        "silence_or_very_quiet",
        "background_noise_or_quiet_audio",
        "possible_speech_or_loud_audio",
    ]

    label_counts = {
        label: sum(r["audio_label"] == label for r in results)
        for label in labels
    }

    total_duration = sum(r["duration_seconds"] for r in results)
    mean_rms = float(np.mean([r["rms_energy"] for r in results]))
    max_rms = max(r["rms_energy"] for r in results)

    summary = {
        "analysis_time": datetime.now().isoformat(timespec="seconds"),
        "segments_analyzed": len(results),
        "total_audio_seconds": round(total_duration, 3),
        "mean_segment_rms": round(mean_rms, 6),
        "maximum_segment_rms": round(max_rms, 6),
        "quiet_segments": label_counts[labels[0]],
        "noise_or_quiet_audio_segments": label_counts[labels[1]],
        "possible_speech_or_loud_segments": label_counts[labels[2]],
        "active_segment_ratio": round(
            label_counts[labels[2]] / len(results), 4
        ),
        "note": "Energy-based estimates only; speech is not verified."
    }

    with open(SESSION_REPORT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)

    print("\nAudio analysis complete!")
    print("Segments analyzed:", len(results))
    print("Total duration:", round(total_duration, 2), "seconds")
    print("Quiet segments:", label_counts[labels[0]])
    print("Noise/quiet audio segments:", label_counts[labels[1]])
    print("Possible speech/loud segments:", label_counts[labels[2]])
    print("\nDetailed report:", SEGMENT_REPORT)
    print("Session summary:", SESSION_REPORT)
    print("\nNote: Labels energy-based estimates hain, verified speech detection nahi.")


if __name__ == "__main__":
    main()
