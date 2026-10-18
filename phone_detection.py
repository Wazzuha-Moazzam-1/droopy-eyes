import cv2
import queue
import threading as thr
import time
from ultralytics import YOLO


# A size of 1 means we only retain the newest available frame.
frame_q = queue.Queue(maxsize=1)

# A nano model is appropriate for an initial real-time detector.
model = YOLO("yolo11n.pt")

# Find the phone class instead of hard-coding a class number.
phone_class_id = next(
    class_id
    for class_id, class_name in model.names.items()
    if class_name == "cell phone"
)


def process_frame(frame_queue, state_queue, stop_event):
    """Run phone detection and display the annotated video."""

    try:
        while not stop_event.is_set():
            try:
                frame = frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            results = model.predict(
                source=frame,
                classes=[phone_class_id],
                conf=0.40,
                imgsz=416,
                verbose=False
            )

            try:
                state_queue.put_nowait({
                    "name": "phone",
                    "confirmed": len(results[0].boxes) > 0,
                    "timestamp": time.monotonic()
                })
            except queue.Full:
                pass

            # plot() returns an annotated NumPy frame.
            annotated_frame = results[0].plot()

            cv2.imshow("Phone Detection", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                stop_event.set()
                break

    finally:
        stop_event.set()
        cv2.destroyAllWindows()


class PhoneDetection(thr.Thread):
    def __init__(self, frame_queue, state_queue, stop_event):
        super().__init__(name="PhoneDetection")
        self.frame_queue = frame_queue
        self.state_queue = state_queue
        self.stop_event = stop_event

    def stop(self):
        self.stop_event.set()

    def run(self):
        process_frame(
            self.frame_queue,
            self.state_queue,
            self.stop_event
        )


if __name__ == "__main__":
    raise SystemExit(
        "Run this detector through Controller.main so it can share the camera."
    )