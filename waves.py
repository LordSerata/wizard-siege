import random
import pygame
import settings as cfg
from enemy import Enemy


class Spawner:
    """Spawns enemies, filtering to world-appropriate types."""

    def __init__(self, difficulty=1.0, world_enemies=None):
        self.elapsed         = 0.0
        self.difficulty      = difficulty
        self._world_enemies  = world_enemies or list(cfg.ENEMY_TYPES.keys())
        start                = cfg.SPAWN_INTERVAL_START * (1.0 / difficulty)
        self._interval_start = max(cfg.SPAWN_INTERVAL_MIN + 0.05, start)
        self._timer          = self._interval_start
        self.active          = True

    @property
    def interval(self):
        t = min(1.0, self.elapsed / cfg.SPAWN_RAMP_SECONDS)
        return self._interval_start + (cfg.SPAWN_INTERVAL_MIN - self._interval_start) * t

    def unlocked(self):
        return [
            (key, data)
            for key, data in cfg.ENEMY_TYPES.items()
            if key in self._world_enemies
            and self.elapsed >= data["unlock_at"]
        ]

    def pick_kind(self):
        options = self.unlocked()
        if not options:
            return self._world_enemies[0]
        keys    = [k for k, _ in options]
        weights = [d["weight"] for _, d in options]
        return random.choices(keys, weights=weights, k=1)[0]

    def spawn_position(self):
        w, h, m = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT, cfg.SPAWN_MARGIN
        edge = random.choice(("top", "bottom", "left", "right"))
        if edge == "top":    return pygame.Vector2(random.uniform(0, w), -m)
        if edge == "bottom": return pygame.Vector2(random.uniform(0, w), h + m)
        if edge == "left":   return pygame.Vector2(-m, random.uniform(0, h))
        return pygame.Vector2(w + m, random.uniform(0, h))

    def make_enemy(self, kind):
        spot = self.spawn_position()
        e = Enemy(spot.x, spot.y, kind)
        e.max_hp = max(1, int(e.max_hp * self.difficulty))
        e.hp     = e.max_hp
        e.speed  = e.speed * (1.0 + (self.difficulty - 1.0) * 0.5)
        return e

    def update(self, dt, enemies):
        if not self.active:
            return
        self.elapsed += dt
        self._timer  -= dt
        if self._timer <= 0:
            enemies.append(self.make_enemy(self.pick_kind()))
            self._timer = self.interval
