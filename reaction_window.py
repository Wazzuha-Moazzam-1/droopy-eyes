import pygame
import queue
import threading
from .reactorclass import Reaction


WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
BACKGROUND_COLOR = (20, 20, 25)


def run_reaction_window(reaction_queue=None, stop_event=None):
    # Configure audio before pygame.init().
    # A smaller buffer can reduce playback delay.
    pygame.mixer.pre_init(
        frequency=44100,
        size=-16,
        channels=2,
        buffer=512
    )

    pygame.init()

    screen = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT)
    )
    pygame.display.set_caption("Slack-Off Reaction")

    clock = pygame.time.Clock()

    reaction = Reaction(
        screen=screen,
        image_path="C:\\Users\\W.Moazzam's laptop\\OneDrive\\Documents\\ALLthePrograms\\Controller\\reactor\\assets\\OIP (1).png",
        sound_path="C:\\Users\\W.Moazzam's laptop\\Downloads\\WhatsApp Audio 2026-10-11 at 10.06.37 PM.mpeg.wav",
        duration_ms=10000
    )

    running = True

    while running and (
        stop_event is None or not stop_event.is_set()
    ):
        # Limits the animation to approximately 60 FPS.
        # Dividing by 1000 converts milliseconds to seconds.
        delta_time = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        if reaction_queue is not None:
            try:
                reaction_queue.get_nowait()
                reaction.trigger()
            except queue.Empty:
                pass

        reaction.update(delta_time)

        screen.fill(BACKGROUND_COLOR)
        reaction.draw()

        pygame.display.flip()

    pygame.quit()


class ReactionWindow(threading.Thread):
    def __init__(self, reaction_queue):
        super().__init__(name="ReactionWindow")
        self.reaction_queue = reaction_queue
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        run_reaction_window(
            self.reaction_queue,
            self.stop_event
        )


if __name__ == "__main__":
    run_reaction_window()