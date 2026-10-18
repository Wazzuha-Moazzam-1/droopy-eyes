
import time
import statistics
from collections import deque

class EyeStateTracker:
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"

    def __init__(
        self,
        smoothing_window=6,
        calibration_samples=90,
        transition_delay=0.12,
        partial_event_duration=3.0,
        closed_event_duration=10.0
    ):
        # Recent valid EAR measurements
        self.ear_history = deque(maxlen=smoothing_window)

        # Startup calibration
        self.calibration_values = []
        self.calibration_samples = calibration_samples
        self.baseline_ear = None

        # Stable-state tracking
        self.confirmed_state = self.UNKNOWN
        self.confirmed_state_started_at = time.monotonic()

        # Pending state transition
        self.candidate_state = None
        self.candidate_started_at = None
        self.transition_delay = transition_delay

        # Event timing
        self.partial_event_duration = partial_event_duration
        self.closed_event_duration = closed_event_duration

        # Ensure each event fires once per episode
        self.partial_event_fired = False
        self.closed_event_fired = False

        # Used for recognizing a blink pattern
        self.closed_started_at = None
        self.last_event = None

    @property
    def calibrated(self):
        return self.baseline_ear is not None

    def calibrate(self, ear):
        """
        Collect open-eye EAR measurements and establish a baseline.

        The user should look normally at the screen with open eyes
        during this stage.
        """

        self.calibration_values.append(ear)

        if len(self.calibration_values) >= self.calibration_samples:
            # Median is less affected by accidental blinks and outliers.
            self.baseline_ear = statistics.median(
                self.calibration_values
            )

            self.ear_history.clear()

    def smooth(self, ear):
        self.ear_history.append(ear)

        return sum(self.ear_history) / len(self.ear_history)

    def classify(self, relative_openness):
        """
        Classify eye geometry relative to the calibrated open-eye state.

        These percentages are starting values. Adjust them after testing.
        """

        current = self.confirmed_state

        # Hysteresis:
        # Slightly stronger evidence is required to enter a lower state
        # than to return to a higher state.

        if current == self.CLOSED:
            if relative_openness >= 0.70:
                return self.OPEN
            elif relative_openness >= 0.48:
                return self.PARTIALLY_CLOSED
            else:
                return self.CLOSED

        if current == self.PARTIALLY_CLOSED:
            if relative_openness >= 0.82:
                return self.OPEN
            elif relative_openness < 0.42:
                return self.CLOSED
            else:
                return self.PARTIALLY_CLOSED

        # OPEN and UNKNOWN use these entry thresholds.
        if relative_openness < 0.42:
            return self.CLOSED
        elif relative_openness < 0.72:
            return self.PARTIALLY_CLOSED
        else:
            return self.OPEN

    def update_confirmed_state(self, candidate, now):
        """
        Promote a candidate state only after it persists for a short
        confirmation period.
        """

        if candidate == self.confirmed_state:
            self.candidate_state = None
            self.candidate_started_at = None
            return False

        if candidate != self.candidate_state:
            self.candidate_state = candidate
            self.candidate_started_at = now
            return False

        candidate_duration = now - self.candidate_started_at

        if candidate_duration < self.transition_delay:
            return False

        previous_state = self.confirmed_state

        self.confirmed_state = candidate
        self.confirmed_state_started_at = now

        self.candidate_state = None
        self.candidate_started_at = None

        self.on_state_change(previous_state, candidate, now)

        return True

    def on_state_change(self, previous_state, new_state, now):
        """
        Reset episode flags and recognize brief closed-eye patterns.
        """

        self.last_event = None

        if new_state == self.CLOSED:
            self.closed_started_at = now
            self.closed_event_fired = False

        if new_state == self.PARTIALLY_CLOSED:
            self.partial_event_fired = False

        if new_state == self.OPEN:
            # A brief CLOSED -> OPEN transition is treated as a blink.
            if (
                previous_state == self.CLOSED
                and self.closed_started_at is not None
            ):
                closure_duration = now - self.closed_started_at

                if closure_duration < self.closed_event_duration:
                    self.last_event = "BLINK"

            self.closed_started_at = None
            self.partial_event_fired = False
            self.closed_event_fired = False

    def detect_duration_event(self, now):
        state_duration = now - self.confirmed_state_started_at

        if (
            self.confirmed_state == self.PARTIALLY_CLOSED
            and state_duration >= self.partial_event_duration
            and not self.partial_event_fired
        ):
            self.partial_event_fired = True
            self.last_event = "SUSTAINED_PARTIAL_CLOSURE"

        elif (
            self.confirmed_state == self.CLOSED
            and state_duration >= self.closed_event_duration
            and not self.closed_event_fired
        ):
            self.closed_event_fired = True
            self.last_event = "PROLONGED_CLOSURE"

    def mark_unknown(self):
        """
        Use this when the face or eye landmarks are unavailable.
        """

        now = time.monotonic()

        self.confirmed_state = self.UNKNOWN
        self.confirmed_state_started_at = now

        self.candidate_state = None
        self.candidate_started_at = None

        self.ear_history.clear()

        return {
            "valid": False,
            "calibrated": self.calibrated,
            "state": self.UNKNOWN,
            "state_duration": 0.0,
            "event": None
        }

    def update(self, raw_ear):
        now = time.monotonic()
        self.last_event = None

        if not self.calibrated:
            self.calibrate(raw_ear)

            return {
                "valid": True,
                "calibrated": False,
                "calibration_progress": (
                    len(self.calibration_values)
                    / self.calibration_samples
                ),
                "raw_ear": raw_ear,
                "state": self.UNKNOWN,
                "event": None
            }

        smoothed_ear = self.smooth(raw_ear)

        relative_openness = smoothed_ear / self.baseline_ear

        candidate = self.classify(relative_openness)

        self.update_confirmed_state(candidate, now)
        self.detect_duration_event(now)

        state_duration = now - self.confirmed_state_started_at

        candidate_duration = 0.0

        if self.candidate_started_at is not None:
            candidate_duration = now - self.candidate_started_at

        return {
            "valid": True,
            "calibrated": True,
            "raw_ear": raw_ear,
            "smoothed_ear": smoothed_ear,
            "baseline_ear": self.baseline_ear,
            "relative_openness": relative_openness,
            "candidate_state": candidate,
            "candidate_duration": candidate_duration,
            "state": self.confirmed_state,
            "state_duration": state_duration,
            "event": self.last_event
        }