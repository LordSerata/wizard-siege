import pygame

import settings as cfg
from gfx import glow_circle


class Bolt:
    """Arcane bolt with glow trail."""

    def __init__(self, origin, target, damage, pierce=0, speed=None):
        self.pos = pygame.Vector2(origin)
        self.target = target
        self.damage = damage
        self.pierce_left = pierce
        self.radius = cfg.BOLT_RADIUS
        self.speed = speed if speed is not None else cfg.BOLT_SPEED
        self.life = cfg.BOLT_LIFETIME
        self.done = False
        self._hit = set()

        heading = target.pos - self.pos
        self.velocity = (
            heading.normalize() * self.speed
            if heading.length() > 0
            else pygame.Vector2(0, -self.speed)
        )

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.done = True
            return

        if self.target is not None and self.target.alive:
            heading = self.target.pos - self.pos
            if heading.length() > 0:
                self.velocity = heading.normalize() * self.speed

        self.pos += self.velocity * dt

        if not (
            -60 <= self.pos.x <= cfg.SCREEN_WIDTH + 60
            and -60 <= self.pos.y <= cfg.SCREEN_HEIGHT + 60
        ):
            self.done = True

    def check_hit(self, enemies):
        hits = []
        for enemy in enemies:
            if id(enemy) in self._hit or not enemy.alive:
                continue
            if self.pos.distance_to(enemy.pos) <= self.radius + enemy.radius:
                enemy.take_damage(self.damage)
                self._hit.add(id(enemy))
                hits.append((enemy, self.damage))
                if self.pierce_left > 0:
                    self.pierce_left -= 1
                else:
                    self.done = True
                    break
        return hits

    def draw(self, surface, offset):
        drawn = self.pos + offset
        glow_circle(surface, cfg.COLOR_BOLT, drawn, self.radius + 2,
                    layers=4, max_alpha=130)
        pygame.draw.circle(surface, cfg.COLOR_BOLT, drawn, self.radius)
        pygame.draw.circle(surface, (255, 255, 255), drawn,
                           max(1, self.radius - 2))
