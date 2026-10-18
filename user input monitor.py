import time
import threading
from pynput import keyboard, mouse


class InputMonitor:
    def __init__(self):
        self.last_activity_time = time.time()
        self.lock = threading.Lock()

        self.keyboard_listener = None
        self.mouse_listener = None

    def record_activity(self):
        with self.lock:
            self.last_activity_time = time.time()

    def on_key_press(self, key):
        self.record_activity()

    def on_mouse_move(self, x, y):
        self.record_activity()

    def on_mouse_click(self, x, y, button, pressed):
        if pressed:
            self.record_activity()

    def on_mouse_scroll(self, x, y, dx, dy):
        self.record_activity()

    def start(self):
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press
        )

        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )

        self.keyboard_listener.start()
        self.mouse_listener.start()

    def get_idle_seconds(self):
        with self.lock:
            return time.time() - self.last_activity_time

    def stop(self):
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
