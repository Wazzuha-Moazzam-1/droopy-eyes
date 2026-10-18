from Controller.eye_phone_detection.eyeDetection import EyeDetection
from Controller.eye_phone_detection.phone_detection import PhoneDetection
from Controller.reactor.reaction_window import ReactionWindow
 # you need to run python -m Controller.main to run this file nahi to nahi chalay gi
import cv2
import queue
import threading
import time

class Controller:
    def __init__(self, state_queue, reaction_queue):
        self.state_queue = state_queue
        self.reaction_queue = reaction_queue

        self.states = {
            "phone": None,
            "eyes_closed": None,
            "looking_away": None
        }

        self.confirmed_since = {
            "phone": None,
            "eyes_closed": None,
            "looking_away": None
        }
        self.reaction_fired = {
            "phone": False,
            "eyes_closed": False,
            "looking_away": False
        }

        self.required_durations = {
            "phone": 10.0,
            "eyes_closed": 10.0,
            "looking_away": 10.0
        }

        self.maximum_state_age = 1.0
        self.running = True

    def receive_state(self):
        while True:
            try:
                state = self.state_queue.get_nowait()
            except queue.Empty:
                return

            self.states[state["name"]] = state

    def state_is_fresh(self, state):
        if state is None:
            return False

        age = time.monotonic() - state["timestamp"]
        return age <= self.maximum_state_age

    def evaluate_state(self, state_name):
        state = self.states[state_name]

        currently_confirmed = (
            self.state_is_fresh(state)
            and state["confirmed"]
        )

        if currently_confirmed:
            if self.confirmed_since[state_name] is None:
                self.confirmed_since[state_name] = state["timestamp"]
        else:
            self.confirmed_since[state_name] = None
            self.reaction_fired[state_name] = False

        if (
            currently_confirmed
            and self.confirmed_since[state_name] is not None
            and time.monotonic() - self.confirmed_since[state_name]
            >= self.required_durations[state_name]
            and not self.reaction_fired[state_name]
        ):
            self.send_reaction(state_name)
            self.reaction_fired[state_name] = True

    def send_reaction(self, reaction_name):
        try:
            self.reaction_queue.put_nowait(reaction_name)
        except queue.Full:
            pass

    def update(self):
        self.receive_state()

        self.evaluate_state("phone")
        self.evaluate_state("eyes_closed")
        self.evaluate_state("looking_away")




if __name__ == "__main__":
    state_queue = queue.Queue()
    reaction_queue = queue.Queue()
    eye_frame_queue = queue.Queue(maxsize=1)
    phone_frame_queue = queue.Queue(maxsize=1)
    stop_event = threading.Event()

    controller = Controller(state_queue, reaction_queue)

    eye_detection = EyeDetection(
        eye_frame_queue,
        state_queue,
        stop_event
    )
    phone_detection = PhoneDetection(
        phone_frame_queue,
        state_queue,
        stop_event
    )
    reaction_window = ReactionWindow(reaction_queue)

    capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not capture.isOpened():
        raise RuntimeError("Could not open the webcam.")

    eye_detection.start()
    phone_detection.start()
    reaction_window.start()

    try:
        while controller.running:
            success, frame = capture.read()

            if not success:
                raise RuntimeError("Could not read a frame from the webcam.")

            for frame_queue in (eye_frame_queue, phone_frame_queue):
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass

                try:
                    frame_queue.put_nowait(frame.copy())
                except queue.Full:
                    pass

            controller.update()
            time.sleep(0.01)
    except KeyboardInterrupt:
        controller.running = False
    finally:
        stop_event.set()
        eye_detection.stop()
        phone_detection.stop()
        reaction_window.stop()
        eye_detection.join()
        phone_detection.join()
        reaction_window.join()
        capture.release()
        cv2.destroyAllWindows()


        # both eye and phone detection are working lekin scene ye hai --- ab kia? this is supposed to trigger the reaction lekin wo nahi hua abhi tak. 