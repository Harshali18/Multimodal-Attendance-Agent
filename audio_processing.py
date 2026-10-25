
import os
import csv
import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy.signal import resample_poly
from fractions import Fraction
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "audio_segments")
CSV_PATH = os.path.join(BASE_DIR, "audio_segments.csv")

SAMPLE_RATE = 16000
SEGMENT_SECONDS = 1
MIC_DEVICE = 5

os.makedirs(OUTPUT_DIR, exist_ok=True)


def preprocess_audio(audio, original_rate):
    # Stereo ko mono mein convert karo
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)

    # Audio ko 16 kHz mein resample karo
    ratio = Fraction(SAMPLE_RATE, original_rate)
    audio = resample_poly(audio, ratio.numerator, ratio.denominator)

    return audio.astype(np.float32)


def save_segments(audio, source, start_time):
    segment_samples = SAMPLE_RATE * SEGMENT_SECONDS
    rows = []

    for index, start in enumerate(range(0, len(audio), segment_samples)):
        segment = audio[start:start + segment_samples]

        if len(segment) == 0:
            continue

        filename = f"{source}_segment_{index:04d}.wav"
        filepath = os.path.join(OUTPUT_DIR, filename)

        sf.write(filepath, segment, SAMPLE_RATE)

        start_seconds = start / SAMPLE_RATE
        end_seconds = (start + len(segment)) / SAMPLE_RATE

        rows.append([
            filename,
            source,
            round(start_seconds, 3),
            round(end_seconds, 3),
            len(segment),
            round(float(np.max(np.abs(segment))), 6),
            round(float(np.sqrt(np.mean(segment ** 2))), 6),
            start_time
        ])

    return rows


def main():
    print("Audio source choose karo:")
    print("1. Microphone se record karo")
    print("2. Existing WAV audio process karo")

    choice = input("Choice (1/2): ").strip()

    if choice == "1":
        duration = input("Kitne seconds record karna hai? ").strip()

        try:
            duration = float(duration)
            if duration <= 0 or duration > 3600:
                raise ValueError
        except ValueError:
            print("Duration 0 se zyada aur 3600 seconds tak honi chahiye.")
            return

        device_info = sd.query_devices(MIC_DEVICE)
        original_rate = int(device_info["default_samplerate"])
        channels = 1

        print(f"Recording start: {duration} seconds tak boliye...")
        audio = sd.rec(
            int(duration * original_rate),
            samplerate=original_rate,
            channels=channels,
            device=MIC_DEVICE,
            dtype="float32"
        )
        sd.wait()

        audio = audio.reshape(-1)
        source = "microphone"
        start_time = datetime.now().isoformat(timespec="milliseconds")

    elif choice == "2":
        filename = input("WAV file ka naam/path enter karo: ").strip().strip('"')

        if not os.path.isabs(filename):
            filename = os.path.join(BASE_DIR, filename)

        if not os.path.isfile(filename):
            print("File nahi mili:", filename)
            return

        audio, original_rate = sf.read(filename, dtype="float32")
        source = os.path.splitext(os.path.basename(filename))[0]
        start_time = datetime.now().isoformat(timespec="milliseconds")

    else:
        print("Invalid choice.")
        return

    if len(audio) == 0:
        print("Audio empty hai.")
        return

    original_duration = len(audio) / original_rate
    processed = preprocess_audio(audio, original_rate)
    rows = save_segments(processed, source, start_time)

    file_exists = os.path.isfile(CSV_PATH)

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists or os.path.getsize(CSV_PATH) == 0:
            writer.writerow([
                "filename",
                "source",
                "start_seconds",
                "end_seconds",
                "sample_count",
                "peak_amplitude",
                "rms_amplitude",
                "recording_start_time"
            ])

        writer.writerows(rows)

    print("\nAudio processing complete!")
    print("Original sample rate:", original_rate, "Hz")
    print("Processed sample rate:", SAMPLE_RATE, "Hz")
    print("Channels: 1 (mono)")
    print("Duration:", round(original_duration, 2), "seconds")
    print("Segments created:", len(rows))
    print("Segments folder:", OUTPUT_DIR)
    print("Metadata CSV:", CSV_PATH)


if __name__ == "__main__":
    main()
