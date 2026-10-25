
import cv2
import os
import csv
from datetime import datetime
from deep_sort_realtime.deepsort_tracker import DeepSort

# Project folder ka path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Face detection XML file
CASCADE_PATH = os.path.join(
    BASE_DIR,
    "haarcascade_frontalface_default.xml"
)

def run_tracking(video_source=0):
    # XML file check
    if not os.path.isfile(CASCADE_PATH):
        print("ERROR: haarcascade_frontalface_default.xml nahi mili.")
        print("XML file ko vision.py ke same folder mein rakho.")
        return

    face_detector = cv2.CascadeClassifier(CASCADE_PATH)

    if face_detector.empty():
        print("ERROR: Face detector XML load nahi hui.")
        return

    # Tracker har run ke liye naya banega
    tracker = DeepSort(
        max_age=30,
        n_init=2,
        max_iou_distance=0.7
    )

    camera = cv2.VideoCapture(video_source)

    if not camera.isOpened():
        print("ERROR: Camera ya video open nahi ho raha.")
        return

    csv_path = os.path.join(BASE_DIR, "tracking_data.csv")

    print("Tracking shuru! Band karne ke liye Q dabao.")
    print("Output file:", csv_path)

    try:
        with open(
            csv_path, "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.writer(csv_file)

            writer.writerow([
                "participant_id",
                "timestamp",
                "x",
                "y",
                "width",
                "height"
            ])

            while True:
                success, frame = camera.read()

                if not success:
                    print("Video khatam ho gaya ya frame nahi mila.")
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                faces = face_detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )

                detections = []

                for (x, y, w, h) in faces:
                    detections.append((
                        [int(x), int(y), int(w), int(h)],
                        0.9,
                        "face"
                    ))

                tracks = tracker.update_tracks(
                    detections,
                    frame=frame
                )

                timestamp = datetime.now().isoformat(
                    timespec="milliseconds"
                )

                for track in tracks:
                    if not track.is_confirmed():
                        continue

                    if track.time_since_update > 0:
                        continue

                    left, top, right, bottom = map(
                        int, track.to_ltrb()
                    )

                    width = right - left
                    height = bottom - top

                    if width <= 0 or height <= 0:
                        continue

                    participant_id = track.track_id

                    cv2.rectangle(
                        frame,
                        (left, top),
                        (right, bottom),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Person {participant_id}",
                        (left, max(top - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )

                    writer.writerow([
                        participant_id,
                        timestamp,
                        left,
                        top,
                        width,
                        height
                    ])

                csv_file.flush()

                cv2.imshow(
                    "Activity 1.1 - Face Tracking",
                    frame
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("Tracking band ho gayi.")
        print("Data saved:", csv_path)


if __name__ == "__main__":
    print("\nVideo source select karo:")
    print("1. Live webcam")
    print("2. Recorded classroom video")

    choice = input("Option (1/2): ").strip()

    if choice == "1":
        run_tracking(0)

    elif choice == "2":
        video_path = input(
            "Video file ka path enter karo: "
        ).strip().strip('"')

        run_tracking(video_path)

    else:
        print("Invalid option. 1 ya 2 enter karo.")
