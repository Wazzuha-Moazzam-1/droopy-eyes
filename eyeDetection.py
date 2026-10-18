import cv2
import math
import threading
import queue
import time
from mediapipe.python.solutions import face_mesh
from queue import Empty
from collections import deque
from . import eyeClass

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

eye_q = queue.Queue(maxsize=10)

def smooth_q(eye_queue):
    values = []

    while True:
        try:
            values.append(eye_queue.get_nowait())
        except Empty:
            break

    return sum(values) / len(values) if values else 0


def landmark_to_pixel(landmark, frame_width, frame_height):
    x = int(landmark.x * frame_width)
    y = int(landmark.y * frame_height)

    return x, y


def action(frame_queue, state_queue, stop_event=None):

    eye_tracker = eyeClass.EyeStateTracker(
    smoothing_window=6,
    calibration_samples=90,

    # Short confirmation to stop rapid state flickering
    transition_delay=0.12,

    # A sustained closure is required before the event is emitted.
    partial_event_duration=3.0,
    closed_event_duration=10.0
    )


    mesh_detector = face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )


    while stop_event is None or not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mesh_detector.process(rgb_frame)

        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            frame_height, frame_width, _ = frame.shape

            left_eye_points = []
            right_eye_points = []

            for index in LEFT_EYE:
                landmark = face_landmarks.landmark[index]

                point = landmark_to_pixel(
                    landmark,
                    frame_width,
                    frame_height
                )

                left_eye_points.append(point)
                cv2.circle(frame, point, 2, (0, 255, 0), -1)

            for index in RIGHT_EYE:
                landmark = face_landmarks.landmark[index]

                point = landmark_to_pixel(
                    landmark,
                    frame_width,
                    frame_height
                )

                right_eye_points.append(point)
                cv2.circle(frame, point, 2, (255, 0, 0), -1)

            left_EAR = calculate_EAR(left_eye_points)
            right_EAR = calculate_EAR(right_eye_points)
                
            average_EAR = (left_EAR + right_EAR )/ 2
            eye_result = eye_tracker.update(average_EAR)
            try:
                state_queue.put_nowait({
                    "name": "eyes_closed",
                    "confirmed": eye_result["state"] == eyeClass.EyeStateTracker.CLOSED,
                    "timestamp": time.monotonic()
                })
            except queue.Full:
                pass
            eye_q.put(average_EAR)
        
            if eye_q.full():
                smooth_val = smooth_q(eye_q)
                eye_q.queue.clear()
                print(smooth_val)
            
            if not eye_result["calibrated"]:
                progress = eye_result.get("calibration_progress", 0.0)

                cv2.putText(
                    frame,
                    f"Calibrating: {progress * 100:.0f}%",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )

            else:
                state = eye_result["state"]
                event = eye_result["event"]

                cv2.putText(
                    frame,
                    f"Raw EAR: {eye_result['raw_ear']:.3f}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )
                
                cv2.putText(
                    frame,
                    f"Smooth: {eye_result['smoothed_ear']:.3f}",
                    (20, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"Openness: {eye_result['relative_openness'] * 100:.0f}%",
                    (20, 95),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,      (255, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"State: {state}",
                    (20, 125),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Duration: {eye_result['state_duration']:.2f}s",
                    (20, 155),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                if event is not None:
                    cv2.putText(
                        frame,
                        f"EVENT: {event}",
                        (20, 195),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2
                    )

            cv2.imshow("Eye Landmarks", frame)


        else:
           #  print
            eye_result = eye_tracker.mark_unknown()
            try:
                state_queue.put_nowait({
                    "name": "eyes_closed",
                    "confirmed": False,
                    "timestamp": time.monotonic()
                })
            except queue.Full:
                pass




        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    mesh_detector.close()
    cv2.destroyAllWindows()


class EyeDetection(threading.Thread):
    def __init__(self, frame_queue, state_queue, stop_event):
        super().__init__(name="EyeDetection")
        self.frame_queue = frame_queue
        self.state_queue = state_queue
        self.stop_event = stop_event

    def stop(self):
        self.stop_event.set()

    def run(self):
        action(self.frame_queue, self.state_queue, self.stop_event)


def dist(p_a: tuple,p_b: tuple):
    x1,y1 = p_a
    x2,y2 = p_b
    delt_x = (x2 - x1) ** 2
    delt_y = (y2 - y1) ** 2
    dist = math.sqrt(delt_x + delt_y)
    return dist


def calculate_EAR(eye_points):
    vertical_1 = dist(
        eye_points[1],
        eye_points[5]
        )

    vertical_2 = dist(
        eye_points[2],
        eye_points[4]
    )

    horizontal = dist(
        eye_points[0],
        eye_points[3]
    )

    EAR  = (vertical_1 + vertical_2) / (2 * horizontal)
    return EAR



# add delay for readings and store them in a queue 
# smooth the readings 
# make eye state            take 5 values then just smooth them and clear the buffer? would that be efficient> like if buffer full then take average and clear buffer
# return time in a particular time

# after implementing this function clear the queue
    