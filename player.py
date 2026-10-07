import math

import pygame

import settings as cfg
from gfx import glow_circle
from projectile import Bolt


class Wizard:
    """Stationary caster at the center of the siege."""

    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.radius = cfg.WIZARD_RADIUS
        self.max_hp = cfg.WIZARD_MAX_HP
        self.hp = self.max_hp
        self.range = cfg.WIZARD_RANGE
        self.cooldown = cfg.WIZARD_COOLDOWN
        self.damage = cfg.WIZARD_DAMAGE
        self.regen = cfg.WIZARD_REGEN
        self.multishot = cfg.WIZARD_MULTISHOT
        self.pierce = cfg.BOLT_PIERCE
        self.bolt_speed = cfg.BOLT_SPEED

        self.mana = cfg.MANA_START
        self.upgrade_levels = {k: 0 for k in cfg.SHOP_COSTS}
        self.spells = []    # active spell keys, set by apply_spells_to_wizard

        self._cast_timer = 0.0
        self._spin = 0.0
        self._bob = 0.0

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def acquire_targets(self, enemies, count):
        in_range = [
            (self.pos.distance_to(e.pos), e)
            for e in enemies
            if self.pos.distance_to(e.pos) <= self.range
        ]
        in_range.sort(key=lambda pair: pair[0])
        return [e for _, e in in_range[:count]]

    def update(self, dt, enemies, bolts):
        self._spin = (self._spin + dt * 1.6) % (math.pi * 2)
        self._bob = (self._bob + dt * 2.2) % (math.pi * 2)

        if self.regen > 0:
            self.heal(self.regen * dt)

        self._cast_timer -= dt
        if self._cast_timer > 0:
            return

        targets = self.acquire_targets(enemies, self.multishot)
        if targets:
            for target in targets:
                bolts.append(
                    Bolt(self.pos, target, self.damage, self.pierce, self.bolt_speed)
                )
            self._cast_timer = self.cooldown

    def draw(self, surface, offset):
        drawn = self.pos + offset
        bob = math.sin(self._bob) * 2.5

        # Ward ring glow
        glow_circle(surface, cfg.COLOR_WARD, drawn, int(self.range),
                    layers=2, max_alpha=30)
        pygame.draw.circle(surface, cfg.COLOR_WARD, drawn, int(self.range), 1)

        # Orbiting motes with glow
        for i in range(self.multishot):
            angle = self._spin + (math.pi * 2 / max(1, self.multishot)) * i
            orbit = self.radius + 14
            mote = drawn + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit
            glow_circle(surface, cfg.COLOR_BOLT, mote, 5, layers=3, max_alpha=100)
            pygame.draw.circle(surface, cfg.COLOR_BOLT, mote, 3)
            pygame.draw.circle(surface, (255, 255, 255), mote, 1)

        cx, cy = drawn.x, drawn.y + bob

        # Robe
        robe_pts = [
            (cx - 10, cy + 2),
            (cx + 10, cy + 2),
            (cx + 14, cy + 26),
            (cx - 14, cy + 26),
        ]
        pygame.draw.polygon(surface, (60, 80, 160), robe_pts)
        pygame.draw.polygon(surface, (80, 110, 200), robe_pts, 1)

        # Robe hem sparkle
        for dx in (-10, -4, 4, 10):
            glow_circle(surface, cfg.COLOR_BOLT, (int(cx + dx), int(cy + 25)),
                        3, layers=2, max_alpha=80)
            pygame.draw.circle(surface, cfg.COLOR_BOLT,
                               (int(cx + dx), int(cy + 25)), 2)

        # Head
        pygame.draw.circle(surface, (220, 185, 150), (int(cx), int(cy)), 10)

        # Glowing eyes
        for ex in (-4, 4):
            glow_circle(surface, (80, 140, 255), (int(cx + ex), int(cy - 1)),
                        4, layers=2, max_alpha=120)
            pygame.draw.circle(surface, cfg.COLOR_WIZARD_CORE,
                               (int(cx + ex), int(cy - 1)), 3)
            pygame.draw.circle(surface, (80, 140, 255),
                               (int(cx + ex), int(cy - 1)), 2)

        # Hat brim
        brim_pts = [
            (cx - 14, cy - 8), (cx + 14, cy - 8),
            (cx + 10, cy - 10), (cx - 10, cy - 10),
        ]
        pygame.draw.polygon(surface, (30, 20, 60), brim_pts)

        # Hat cone
        hat_pts = [
            (cx - 10, cy - 10), (cx + 10, cy - 10),
            (cx + 2,  cy - 32), (cx - 2,  cy - 32),
        ]
        pygame.draw.polygon(surface, (45, 30, 90), hat_pts)
        pygame.draw.polygon(surface, (90, 60, 160), hat_pts, 1)

        # Star on hat
        self._draw_star(surface, (cx + 1, cy - 28), 4, (255, 240, 120))
        glow_circle(surface, (255, 220, 80), (int(cx + 1), int(cy - 28)),
                    5, layers=2, max_alpha=80)

        # Staff
        staff_x = cx - 16
        pygame.draw.line(surface, (120, 90, 60),
                         (staff_x, cy + 22), (staff_x - 2, cy - 20), 3)
        glow_circle(surface, cfg.COLOR_BOLT,
                    (int(staff_x - 2), int(cy - 22)), 7, layers=3, max_alpha=120)
        pygame.draw.circle(surface, cfg.COLOR_BOLT,
                           (int(staff_x - 2), int(cy - 22)), 5)
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(staff_x - 2), int(cy - 22)), 2)

    def _draw_star(self, surface, center, r, color):
        cx, cy = center
        pts = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            radius = r if i % 2 == 0 else r * 0.45
            pts.append((
                cx + math.cos(angle) * radius,
                cy - math.sin(angle) * radius,
            ))
        pygame.draw.polygon(surface, color, pts)
