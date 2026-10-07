import math
import random

import pygame

import settings as cfg


class Enemy:
    """Besieger that walks straight at the wizard."""

    def __init__(self, x, y, kind="goblin"):
        data = cfg.ENEMY_TYPES[kind]
        self.kind = kind
        self.name = data["name"]
        self.pos = pygame.Vector2(x, y)
        self.max_hp = data["hp"]
        self.hp = self.max_hp
        self.speed = data["speed"]
        self.radius = data["radius"]
        self.damage = data["damage"]
        self.color = data["color"]
        self.mana = data["mana"]
        self.on_death = data.get("on_death")
        self._contact_cooldown = data["contact_cooldown"]
        self._contact_timer = 0.0
        self._flash = 0.0
        self._wobble = random.uniform(0, math.pi * 2)

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp -= amount
        self._flash = cfg.HIT_FLASH_TIME

    def spawn_on_death(self):
        if not self.on_death:
            return []
        children = []
        for _ in range(self.on_death["count"]):
            offset = pygame.Vector2(
                random.uniform(-18, 18), random.uniform(-18, 18)
            )
            spot = self.pos + offset
            children.append(Enemy(spot.x, spot.y, self.on_death["kind"]))
        return children

    def update(self, dt, wizard):
        self._contact_timer -= dt
        self._flash = max(0.0, self._flash - dt)
        self._wobble = (self._wobble + dt * 4.0) % (math.pi * 2)

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

    # --- drawing ---

    def draw(self, surface, offset):
        flash = self._flash > 0
        drawn = self.pos + offset
        cx, cy = drawn.x, drawn.y

        draw_fn = {
            "goblin":      self._draw_goblin,
            "wraith":      self._draw_wraith,
            "ogre":        self._draw_ogre,
            "revenant":    self._draw_revenant,
            "thornling":   self._draw_thornling,
            "shade":       self._draw_shade,
            "gargoyle":    self._draw_gargoyle,
            "bone_knight": self._draw_bone_knight,
            "magma_brute": self._draw_magma_brute,
            "cinder_wisp": self._draw_cinder_wisp,
            "void_stalker":self._draw_void_stalker,
            "rift_horror": self._draw_rift_horror,
        }.get(self.kind)
        if draw_fn:
            draw_fn(surface, cx, cy, flash)

        self._draw_hp_bar(surface, drawn)

    def _col(self, flash):
        if flash:
            return (255, 255, 255)
        if getattr(self, "frozen", False):
            # Blend color toward icy blue
            return tuple(min(255, int(c * 0.5 + ic * 0.5))
                         for c, ic in zip(self.color, (140, 220, 255)))
        return self.color

    def _draw_hp_bar(self, surface, drawn):
        if self.hp >= self.max_hp:
            return
        w, h = self.radius * 2, 4
        x = drawn.x - self.radius
        y = drawn.y - self.radius - 9
        pct = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, cfg.COLOR_HP_BG, (x, y, w, h))
        pygame.draw.rect(surface, cfg.COLOR_HP_FG, (x, y, w * pct, h))

    # --- goblin ---
    def _draw_goblin(self, surface, cx, cy, flash):
        c = self._col(flash)
        # Body - hunched oval
        pygame.draw.ellipse(surface, c, (cx - 9, cy - 4, 18, 16))
        # Head - slightly offset upward and forward
        pygame.draw.circle(surface, c, (int(cx + 2), int(cy - 10)), 8)
        # Ears - pointy triangles
        for side in (-1, 1):
            ear = [
                (cx + 2 + side * 6, cy - 14),
                (cx + 2 + side * 14, cy - 20),
                (cx + 2 + side * 8, cy - 8),
            ]
            pygame.draw.polygon(surface, c, ear)
        # Eyes - beady
        for ex in (-3, 3):
            eye_color = (255, 80, 80) if not flash else (200, 200, 200)
            pygame.draw.circle(surface, eye_color, (int(cx + 2 + ex), int(cy - 11)), 2)
        # Weapon - little club
        pygame.draw.line(surface, (120, 80, 40),
                         (cx - 10, cy + 4), (cx - 18, cy - 8), 3)
        pygame.draw.circle(surface, (100, 70, 30), (int(cx - 18), int(cy - 8)), 4)

    # --- wraith ---
    def _draw_wraith(self, surface, cx, cy, flash):
        c = self._col(flash)
        bob = math.sin(self._wobble) * 3

        # Wispy tail - fading triangles below
        for i in range(3):
            alpha_col = tuple(max(0, v - i * 50) for v in c)
            tail_pts = [
                (cx - 6 + i * 2, cy + 6 + i * 7 + bob),
                (cx + 6 - i * 2, cy + 6 + i * 7 + bob),
                (cx + random.randint(-2, 2), cy + 18 + i * 7 + bob),
            ]
            pygame.draw.polygon(surface, alpha_col, tail_pts)

        # Hood/body - teardrop
        body_pts = [
            (cx, cy - 14 + bob),
            (cx - 10, cy + bob),
            (cx - 7, cy + 10 + bob),
            (cx + 7, cy + 10 + bob),
            (cx + 10, cy + bob),
        ]
        pygame.draw.polygon(surface, c, body_pts)

        # Hollow eye sockets
        eye_col = (20, 10, 40) if not flash else (180, 180, 180)
        for ex in (-4, 4):
            pygame.draw.ellipse(surface, eye_col,
                                (cx + ex - 3, cy - 6 + bob, 6, 5))

    # --- ogre ---
    def _draw_ogre(self, surface, cx, cy, flash):
        c = self._col(flash)
        # Wide squat body
        pygame.draw.rect(surface, c, (cx - 18, cy - 4, 36, 26), border_radius=4)
        # Round head
        pygame.draw.circle(surface, c, (int(cx), int(cy - 14)), 14)
        # Horns
        for side in (-1, 1):
            horn = [
                (cx + side * 8, cy - 24),
                (cx + side * 14, cy - 36),
                (cx + side * 12, cy - 22),
            ]
            pygame.draw.polygon(surface, c, horn)
            pygame.draw.polygon(surface, (80, 50, 30), horn, 1)
        # Eyes - mean squint
        eye_col = (255, 60, 20) if not flash else (200, 200, 200)
        for ex in (-5, 5):
            pygame.draw.ellipse(surface, eye_col,
                                (cx + ex - 4, cy - 17, 8, 5))
        # Nose
        pygame.draw.circle(surface, (160, 90, 60), (int(cx), int(cy - 10)), 3)
        # Fists
        for side in (-1, 1):
            pygame.draw.circle(surface, c, (int(cx + side * 22), int(cy + 10)), 7)

    # --- revenant ---
    def _draw_revenant(self, surface, cx, cy, flash):
        c = self._col(flash)
        pulse = abs(math.sin(self._wobble)) * 0.3 + 0.7

        # Ghostly cloak
        cloak_pts = [
            (cx, cy - 18),
            (cx - 14, cy + 4),
            (cx - 10, cy + 20),
            (cx - 4, cy + 14),
            (cx, cy + 18),
            (cx + 4, cy + 14),
            (cx + 10, cy + 20),
            (cx + 14, cy + 4),
        ]
        pygame.draw.polygon(surface, c, cloak_pts)

        # Skull face
        skull_col = (230, 225, 210) if not flash else (255, 255, 255)
        pygame.draw.circle(surface, skull_col, (int(cx), int(cy - 6)), 11)

        # Eye sockets - dark hollow
        socket_col = (30, 10, 50) if not flash else (180, 180, 180)
        for ex in (-4, 4):
            pygame.draw.ellipse(surface, socket_col,
                                (cx + ex - 4, cy - 11, 8, 7))
            # Purple glow inside
            glow = (int(180 * pulse), 0, int(220 * pulse))
            pygame.draw.ellipse(surface, glow,
                                (cx + ex - 2, cy - 9, 4, 4))

        # Teeth
        for tx in (-4, 0, 4):
            pygame.draw.rect(surface, skull_col,
                             (cx + tx - 2, cy - 1, 3, 5))

    # --- thornling (world 1 — fast green spiked creature) ---
    def _draw_thornling(self, surface, cx, cy, flash):
        c = self._col(flash)
        bob = math.sin(self._wobble) * 2
        # Squat spiky body
        pygame.draw.ellipse(surface, c, (cx - 8, cy - 6 + bob, 16, 14))
        # Spikes around body
        for i in range(6):
            a = i * math.pi / 3 + self._wobble * 0.3
            sx = cx + math.cos(a) * 10
            sy = cy + math.sin(a) * 8 + bob
            tip = (cx + math.cos(a) * 16, cy + math.sin(a) * 14 + bob)
            l = (sx - math.sin(a) * 3, sy + math.cos(a) * 3)
            r = (sx + math.sin(a) * 3, sy - math.cos(a) * 3)
            pygame.draw.polygon(surface, c, [l, r, tip])
        # Eyes
        eye_col = (255, 200, 0) if not flash else (255, 255, 255)
        for ex in (-3, 3):
            pygame.draw.circle(surface, eye_col,
                               (int(cx + ex), int(cy - 3 + bob)), 2)

    # --- shade (world 1 — wispy fast shadow) ---
    def _draw_shade(self, surface, cx, cy, flash):
        c = self._col(flash)
        bob = math.sin(self._wobble * 1.5) * 4
        pulse = abs(math.sin(self._wobble))
        # Dark wispy form — semi-transparent layers
        for i in range(3):
            alpha = int((80 - i * 20) * pulse)
            r = 12 - i * 3
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (*c, max(0, alpha)),
                                (0, i * 2, r*2, r*2 - i*2))
            surface.blit(s, (cx - r - 1, cy - r + bob - 1))
        # Solid core
        pygame.draw.ellipse(surface, c, (cx - 6, cy - 8 + bob, 12, 14))
        # Two glowing eyes
        eye_col = (200, 220, 255) if not flash else (255, 255, 255)
        for ex in (-3, 3):
            pygame.draw.circle(surface, eye_col,
                               (int(cx + ex), int(cy - 4 + bob)), 2)
            glow_s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (*eye_col, 80), (4, 4), 4)
            surface.blit(glow_s, (int(cx + ex) - 4, int(cy - 4 + bob) - 4))

    # --- gargoyle (world 2 — heavy stone flier) ---
    def _draw_gargoyle(self, surface, cx, cy, flash):
        c = self._col(flash)
        # Wide stone body
        pygame.draw.rect(surface, c, (cx - 16, cy - 8, 32, 22),
                         border_radius=3)
        # Head
        pygame.draw.circle(surface, c, (int(cx), int(cy - 16)), 12)
        # Stone horns
        for side in (-1, 1):
            horn = [(cx + side*6, cy - 24),
                    (cx + side*12, cy - 36),
                    (cx + side*10, cy - 22)]
            dark = tuple(max(0, v - 30) for v in c)
            pygame.draw.polygon(surface, c, horn)
            pygame.draw.polygon(surface, dark, horn, 1)
        # Wings — angular stone slabs
        for side in (-1, 1):
            wing = [(cx + side*16, cy - 4),
                    (cx + side*30, cy - 18),
                    (cx + side*28, cy + 8),
                    (cx + side*14, cy + 10)]
            dark = tuple(max(0, v - 40) for v in c)
            pygame.draw.polygon(surface, dark, wing)
            pygame.draw.polygon(surface, c, wing, 1)
        # Red eyes
        eye_col = (220, 40, 40) if not flash else (255, 255, 255)
        for ex in (-4, 4):
            pygame.draw.ellipse(surface, eye_col,
                                (cx + ex - 4, cy - 20, 8, 6))

    # --- bone_knight (world 2 — skeletal warrior) ---
    def _draw_bone_knight(self, surface, cx, cy, flash):
        c = self._col(flash)
        dark = tuple(max(0, v - 50) for v in c)
        # Armored torso
        pygame.draw.rect(surface, c, (cx - 10, cy - 8, 20, 18),
                         border_radius=2)
        pygame.draw.rect(surface, dark, (cx - 10, cy - 8, 20, 18), 1,
                         border_radius=2)
        # Skull head
        pygame.draw.circle(surface, c, (int(cx), int(cy - 18)), 10)
        # Eye sockets
        socket = (30, 20, 10) if not flash else (180, 180, 180)
        for ex in (-3, 3):
            pygame.draw.ellipse(surface, socket,
                                (cx + ex - 3, cy - 22, 7, 6))
        # Shield
        shield = [(cx - 14, cy - 6), (cx - 20, cy),
                  (cx - 18, cy + 10), (cx - 10, cy + 12), (cx - 8, cy - 4)]
        pygame.draw.polygon(surface, dark, shield)
        pygame.draw.polygon(surface, c, shield, 1)
        # Sword
        pygame.draw.line(surface, c,
                         (cx + 12, cy + 14), (cx + 18, cy - 14), 3)
        pygame.draw.line(surface, dark,
                         (cx + 10, cy - 8), (cx + 20, cy - 8), 2)

    # --- magma_brute (world 3 — huge lava creature) ---
    def _draw_magma_brute(self, surface, cx, cy, flash):
        c = self._col(flash)
        pulse = abs(math.sin(self._wobble * 0.7))
        # Massive rocky body
        pygame.draw.ellipse(surface, c, (cx - 22, cy - 10, 44, 36))
        # Lava cracks glowing inside
        if not flash:
            lava = (min(255, int(200 + pulse * 55)), int(60 * pulse), 0)
            for i in range(4):
                a = self._wobble + i * math.pi / 2
                x1 = int(cx + math.cos(a) * 6)
                y1 = int(cy + math.sin(a) * 8)
                x2 = int(cx + math.cos(a) * 18)
                y2 = int(cy + math.sin(a) * 14)
                pygame.draw.line(surface, lava, (x1, y1), (x2, y2), 2)
        # Blocky head
        pygame.draw.rect(surface, c, (cx - 16, cy - 30, 32, 24),
                         border_radius=3)
        # Glowing eyes
        eye_col = (min(255, int(220 + pulse * 35)),
                   int(80 * pulse), 0) if not flash else (255, 255, 255)
        for ex in (-6, 6):
            pygame.draw.ellipse(surface, eye_col,
                                (cx + ex - 5, cy - 24, 10, 8))
        # Rocky fists
        for side in (-1, 1):
            pygame.draw.circle(surface, c,
                               (int(cx + side * 26), int(cy + 8)), 10)

    # --- cinder_wisp (world 3 — tiny fast fire sprite) ---
    def _draw_cinder_wisp(self, surface, cx, cy, flash):
        c = self._col(flash)
        pulse = abs(math.sin(self._wobble * 2))
        bob = math.sin(self._wobble) * 3
        # Flame core
        flame_col = (min(255, int(255 * (0.7 + pulse * 0.3))),
                     int(140 * pulse), 0) if not flash else (255, 255, 255)
        pygame.draw.circle(surface, flame_col,
                           (int(cx), int(cy + bob)), 7)
        # Outer glow
        glow_s = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (*c, int(100 * pulse)), (12, 12), 11)
        surface.blit(glow_s, (int(cx) - 12, int(cy + bob) - 12))
        # Spark tips
        for i in range(4):
            a = self._wobble * 2 + i * math.pi / 2
            sx = int(cx + math.cos(a) * 9)
            sy = int(cy + math.sin(a) * 6 + bob)
            pygame.draw.circle(surface, flame_col, (sx, sy), 2)

    # --- void_stalker (world 4 — fast purple hunter) ---
    def _draw_void_stalker(self, surface, cx, cy, flash):
        c = self._col(flash)
        pulse = abs(math.sin(self._wobble))
        bob = math.sin(self._wobble * 1.2) * 2
        # Elongated angular body
        body = [(cx, cy - 16 + bob),
                (cx - 10, cy - 4 + bob),
                (cx - 8, cy + 10 + bob),
                (cx + 8, cy + 10 + bob),
                (cx + 10, cy - 4 + bob)]
        pygame.draw.polygon(surface, c, body)
        dark = tuple(max(0, v - 60) for v in c)
        pygame.draw.polygon(surface, dark, body, 1)
        # Void tendrils
        for i in range(3):
            a = math.pi + i * math.pi / 3 + self._wobble * 0.5
            tx = int(cx + math.cos(a) * 14)
            ty = int(cy + 8 + math.sin(a) * 6 + bob)
            pygame.draw.line(surface, dark, (int(cx), int(cy + 8 + bob)),
                             (tx, ty), 2)
        # Glowing void eyes
        eye_col = (min(255, int(180 + pulse * 75)),
                   0, 255) if not flash else (255, 255, 255)
        for ex in (-4, 4):
            pygame.draw.circle(surface, eye_col,
                               (int(cx + ex), int(cy - 8 + bob)), 3)
            gs = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*eye_col, int(120 * pulse)), (5, 5), 5)
            surface.blit(gs, (int(cx + ex) - 5, int(cy - 8 + bob) - 5))

    # --- rift_horror (world 4 — massive void entity) ---
    def _draw_rift_horror(self, surface, cx, cy, flash):
        c = self._col(flash)
        pulse = abs(math.sin(self._wobble * 0.5))
        # Pulsing void mass
        for layer in range(4, 0, -1):
            r = self.radius - layer * 2 + int(pulse * 4)
            alpha = int(60 + layer * 30)
            dark = tuple(max(0, int(v * (layer / 4))) for v in c)
            ls = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ls, (*dark, alpha), (r+1, r+1), r)
            surface.blit(ls, (cx - r - 1, cy - r - 1))
        # Solid core
        pygame.draw.circle(surface, c, (int(cx), int(cy)), self.radius - 8)
        # Rift cracks
        if not flash:
            crack_col = (min(255, int(180 + pulse * 75)), 0, 255)
            for i in range(5):
                a = self._wobble * 0.3 + i * math.pi * 2 / 5
                x1 = int(cx + math.cos(a) * 6)
                y1 = int(cy + math.sin(a) * 6)
                x2 = int(cx + math.cos(a) * (self.radius - 4))
                y2 = int(cy + math.sin(a) * (self.radius - 4))
                pygame.draw.line(surface, crack_col, (x1, y1), (x2, y2), 2)
        # Eyes — ring of glowing orbs
        eye_col = (200, 0, 255) if not flash else (255, 255, 255)
        for i in range(6):
            a = self._wobble * 0.4 + i * math.pi / 3
            ex = int(cx + math.cos(a) * 14)
            ey = int(cy + math.sin(a) * 14)
            pygame.draw.circle(surface, eye_col, (ex, ey), 4)
