import random

import pygame

import settings as cfg


class DamageNumber:
    """Short-lived number that floats up from a hit."""

    def __init__(self, pos, amount, color=(255, 240, 200)):
        self.origin = pygame.Vector2(pos)
        self.text = str(int(amount))
        self.color = color
        self.life = cfg.DAMAGE_NUMBER_LIFETIME
        self.drift = random.uniform(-14, 14)
        self.done = False

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.done = True

    def draw(self, surface, font, offset):
        t = 1.0 - (self.life / cfg.DAMAGE_NUMBER_LIFETIME)
        pos = self.origin + offset + pygame.Vector2(
            self.drift * t, -cfg.DAMAGE_NUMBER_RISE * t
        )
        alpha = max(0, int(255 * (1.0 - t)))
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, surf.get_rect(center=pos))


class ScreenShake:
    """Decaying random camera offset."""

    def __init__(self):
        self.amount = 0.0

    def add(self, amount):
        self.amount = min(14.0, self.amount + amount)

    def update(self, dt):
        self.amount = max(0.0, self.amount - cfg.SHAKE_DECAY * dt)

    @property
    def offset(self):
        if self.amount <= 0:
            return pygame.Vector2(0, 0)
        return pygame.Vector2(
            random.uniform(-self.amount, self.amount),
            random.uniform(-self.amount, self.amount),
        )
