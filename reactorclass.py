import pygame

class Reaction:
    def __init__(
        self,
        screen,
        image_path,
        sound_path,
        duration_ms=3000
    ):
        self.screen = screen
        self.duration_ms = duration_ms

        # Load the visual once, not every time the reaction starts.
        original_image = pygame.image.load(image_path).convert_alpha() 
            original_image,
            (180, 180)
        )

        # Rect stores the image position and dimensions.
        self.rect = self.image.get_rect()

        # Movement speed in pixels per second.
        self.velocity = pygame.Vector2(450, 320)

        # Short sound effect loaded into memory.
        self.sound = pygame.mixer.Sound(sound_path)
        self.sound.set_volume(0.9)

        self.active = False
        self.started_at = 0

    def trigger(self):
        """Start the reaction unless it is already playing."""

        if self.active:
            return

        self.active = True
        self.started_at = pygame.time.get_ticks()

        # Start near the upper-left area of the window.
        self.rect.topleft = (30, 30)

        # Play exactly once when the reaction begins.
        self.sound.play()

    def update(self, delta_time):
        """Update movement and stop after the chosen duration."""

        if not self.active:
            return

        # Movement is multiplied by elapsed time, making it
        # independent of the computer's frame rate.
        self.rect.x += round(self.velocity.x * delta_time)
        self.rect.y += round(self.velocity.y * delta_time)

        screen_rect = self.screen.get_rect()

        # Bounce horizontally.
        if self.rect.left <= screen_rect.left:
            self.rect.left = screen_rect.left
            self.velocity.x = abs(self.velocity.x)

        elif self.rect.right >= screen_rect.right:
            self.rect.right = screen_rect.right
            self.velocity.x = -abs(self.velocity.x)

        # Bounce vertically.
        if self.rect.top <= screen_rect.top:
            self.rect.top = screen_rect.top
            self.velocity.y = abs(self.velocity.y)

        elif self.rect.bottom >= screen_rect.bottom:
            self.rect.bottom = screen_rect.bottom
            self.velocity.y = -abs(self.velocity.y)

        elapsed = pygame.time.get_ticks() - self.started_at

        if elapsed >= self.duration_ms:
            self.stop()

    def draw(self):
        """Draw the reaction only while it is active."""

        if self.active:
            self.screen.blit(self.image, self.rect)

    def stop(self):
        self.active = False
        self.sound.stop()

        # i dont want it to have a hardcoded duration, the trigger shold stop when the user clicks on it, so technically the user should wake up and stop it themselves
        
