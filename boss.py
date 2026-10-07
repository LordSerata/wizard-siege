"""
Boss enemy — spawns every 10 levels, drops Soul Shards.
Drawn as a distinct large figure so it reads clearly on screen.
"""

import math
import random

import pygame

import settings as cfg
from gfx import glow_circle


class Boss:
    """A massive corrupted sorcerer that blocks the next level."""

    def __init__(self, x, y, level):
        # Stats scale with how deep the run is
        scale = 1.0 + (level / 10) * 0.5
        self.pos = pygame.Vector2(x, y)
        self.max_hp = int(300 * scale)
        self.hp = self.max_hp
        self.speed = max(28, int(55 * (1.0 - level * 0.01)))
        self.radius = 32
        self.damage = int(20 * scale)
        self._contact_cooldown = 1.0
        self._contact_timer = 0.0
        self._flash = 0.0
        self._spin = random.uniform(0, math.pi * 2)
        self._pulse = 0.0
        self.mana = 0           # no mana drop, gives shards instead
        self.shards = max(1, level // 3 + 1)
        self.alive_flag = True
        self.on_death = None    # compatible with enemy interface
        self.kind = "boss"
        self.name = "Dread Sorcerer"
        self.essence = 0

    @property
    def alive(self):
        return self.alive_flag

    def take_damage(self, amount):
        self.hp -= amount
        self._flash = cfg.HIT_FLASH_TIME
        if self.hp <= 0:
            self.alive_flag = False

    def spawn_on_death(self):
        return []

    def update(self, dt, wizard):
        self._contact_timer -= dt
        self._flash = max(0.0, self._flash - dt)
        self._spin = (self._spin + dt * 1.2) % (math.pi * 2)
        self._pulse = (self._pulse + dt * 3.0) % (math.pi * 2)

        toward = wizard.pos - self.pos
        dist = toward.length()
        touching = dist <= self.radius + wizard.radius

        if not touching and dist > 0:
            self.pos += toward.normalize() * self.speed * dt
        elif touching and self._contact_timer <= 0:
            wizard.take_damage(self.damage)
            self._contact_timer = self._contact_cooldown
            return self.damage
        return 0

    def draw(self, surface, offset):
        drawn = self.pos + offset
        cx, cy = drawn.x, drawn.y
        flash = self._flash > 0
        pulse = abs(math.sin(self._pulse))

        # Outer dark aura
        aura_r = self.radius + 10 + int(pulse * 6)
        aura_surf = pygame.Surface((aura_r * 2 + 4, aura_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (80, 0, 120, 60),
                           (aura_r + 2, aura_r + 2), aura_r)
        surface.blit(aura_surf, (cx - aura_r - 2, cy - aura_r - 2))

        # Orbiting dark orbs
        for i in range(4):
            angle = self._spin + i * math.pi / 2
            orb = drawn + pygame.Vector2(math.cos(angle), math.sin(angle)) * (self.radius + 4)
            orb_col = (180, 0, 220) if not flash else (255, 255, 255)
            glow_circle(surface, (180, 0, 220), orb, 9, layers=3, max_alpha=120)
            pygame.draw.circle(surface, orb_col, orb, 6)
            pygame.draw.circle(surface, (255, 200, 255), orb, 3)

        # Cloak body
        cloak_col = (100, 20, 140) if not flash else (255, 255, 255)
        cloak_pts = [
            (cx, cy - 30),
            (cx - 24, cy - 8),
            (cx - 28, cy + 18),
            (cx - 12, cy + 30),
            (cx + 12, cy + 30),
            (cx + 28, cy + 18),
            (cx + 24, cy - 8),
        ]
        pygame.draw.polygon(surface, cloak_col, cloak_pts)
        pygame.draw.polygon(surface, (180, 60, 220), cloak_pts, 2)

        # Head
        head_col = (190, 150, 120) if not flash else (255, 255, 255)
        pygame.draw.circle(surface, head_col, (int(cx), int(cy - 16)), 14)

        # Crown of horns
        horn_col = (140, 30, 180) if not flash else (255, 255, 255)
        for i, (hx, hy, hr) in enumerate([
            (-10, -34, 5), (0, -38, 7), (10, -34, 5)
        ]):
            horn_pts = [
                (cx + hx - hr, cy + hy + 8),
                (cx + hx + hr, cy + hy + 8),
                (cx + hx, cy + hy - 6),
            ]
            pygame.draw.polygon(surface, horn_col, horn_pts)

        # Glowing eyes
        eye_glow = (int(200 + pulse * 55), 0, int(180 + pulse * 75))
        for ex in (-5, 5):
            pygame.draw.ellipse(surface, (20, 0, 30),
                                (cx + ex - 5, cy - 21, 10, 8))
            pygame.draw.ellipse(surface, eye_glow,
                                (cx + ex - 3, cy - 19, 6, 5))

        # Staff
        staff_col = (80, 40, 100) if not flash else (255, 255, 255)
        pygame.draw.line(surface, staff_col,
                         (cx + 20, cy + 26), (cx + 26, cy - 26), 4)
        # Staff orb
        orb_col = (int(180 + pulse * 75), 0, 220) if not flash else (255, 255, 255)
        glow_circle(surface, (180, 0, 220),
                    (int(cx + 26), int(cy - 28)), 12, layers=4, max_alpha=140)
        pygame.draw.circle(surface, orb_col, (int(cx + 26), int(cy - 28)), 8)
        pygame.draw.circle(surface, (255, 200, 255), (int(cx + 26), int(cy - 28)), 4)

        # HP bar — wider for boss
        bar_w = self.radius * 3
        bx = cx - bar_w // 2
        by = cy - self.radius - 14
        pct = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, cfg.COLOR_HP_BG, (bx, by, bar_w, 7))
        pygame.draw.rect(surface, (180, 0, 220), (bx, by, bar_w * pct, 7))
        pygame.draw.rect(surface, (220, 100, 255), (bx, by, bar_w, 7), 1)
