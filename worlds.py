"""
World definitions for Wizard Siege.

Each world has:
  - A background renderer (draw_bg)
  - A difficulty multiplier applied on top of per-level scaling
  - Additional enemy types unlocked in this world
  - An unlock threshold (reach level 100 in previous world)
"""

import math
import random
import pygame


# ------------------------------------------------------------------ world data

WORLDS = [
    {
        "id":          0,
        "name":        "The Void",
        "subtitle":    "Where it begins",
        "unlock_at":   0,          # always unlocked
        "diff_mult":   1.0,        # global enemy stat multiplier
        "color_sky":   (14, 12, 22),
        "color_accent": (90, 60, 160),
        "enemies":     ["goblin", "wraith", "ogre", "revenant"],
    },
    {
        "id":          1,
        "name":        "Cursed Forest",
        "subtitle":    "Reach level 100 in The Void",
        "unlock_at":   100,
        "diff_mult":   1.8,
        "color_sky":   (10, 18, 12),
        "color_accent": (60, 140, 60),
        "enemies":     ["goblin", "wraith", "ogre", "revenant", "thornling", "shade"],
    },
    {
        "id":          2,
        "name":        "Dungeon Depths",
        "subtitle":    "Reach level 100 in Cursed Forest",
        "unlock_at":   100,
        "diff_mult":   2.8,
        "color_sky":   (16, 14, 20),
        "color_accent": (120, 90, 50),
        "enemies":     ["goblin", "wraith", "ogre", "revenant",
                        "thornling", "shade", "gargoyle", "bone_knight"],
    },
    {
        "id":          3,
        "name":        "Volcanic Crater",
        "subtitle":    "Reach level 100 in Dungeon Depths",
        "unlock_at":   100,
        "diff_mult":   4.0,
        "color_sky":   (22, 10, 8),
        "color_accent": (200, 80, 20),
        "enemies":     ["goblin", "wraith", "ogre", "revenant",
                        "thornling", "shade", "gargoyle", "bone_knight",
                        "magma_brute", "cinder_wisp"],
    },
    {
        "id":          4,
        "name":        "Astral Plane",
        "subtitle":    "Reach level 100 in Volcanic Crater",
        "unlock_at":   100,
        "diff_mult":   6.0,
        "color_sky":   (8, 8, 24),
        "color_accent": (180, 100, 255),
        "enemies":     ["goblin", "wraith", "ogre", "revenant",
                        "thornling", "shade", "gargoyle", "bone_knight",
                        "magma_brute", "cinder_wisp", "void_stalker", "rift_horror"],
    },
]


def get_world(world_id):
    return WORLDS[min(world_id, len(WORLDS) - 1)]


def is_unlocked(world_id, save_data):
    """World 0 always unlocked. Others need highest_world >= world_id."""
    if world_id == 0:
        return True
    return save_data.get("highest_world", 0) >= world_id


# ------------------------------------------------------------------ world previews

class WorldPreview:
    """Small animated thumbnail drawn above each world select button.

    When locked: dark silhouette only.
    When unlocked + hovered: full-color animation.
    """

    def __init__(self, world_id, w, h):
        self.world_id = world_id
        self.w = w
        self.h = h
        self._t = 0.0
        self._rng = random.Random(world_id * 999 + 7)
        self._surf = pygame.Surface((w, h), pygame.SRCALPHA)
        self._init_static()

    def _init_static(self):
        rng = self._rng
        self._stars  = [(rng.randint(0, self.w), rng.randint(0, self.h),
                         rng.randint(60, 200)) for _ in range(30)]
        self._trees  = [(rng.randint(10, self.w-10), self.h - rng.randint(10, 30),
                         rng.randint(14, 28)) for _ in range(7)]
        self._rocks  = [(rng.randint(5, self.w-5), self.h - rng.randint(4, 14),
                         rng.randint(6, 16)) for _ in range(6)]
        self._orbs   = [(rng.uniform(0, self.w), rng.uniform(0, self.h),
                         rng.uniform(0, math.pi*2)) for _ in range(8)]

    def update(self, dt):
        self._t += dt

    def draw(self, surface, x, y, unlocked, hovered):
        s = self._surf
        s.fill((0, 0, 0, 0))
        t = self._t

        # Background fill
        if not unlocked:
            pygame.draw.rect(s, (14, 12, 22), (0, 0, self.w, self.h))
        else:
            w_colors = {
                0: (14, 12, 22),
                1: (10, 18, 12),
                2: (16, 14, 20),
                3: (22, 10, 8),
                4: (8, 8, 24),
            }
            pygame.draw.rect(s, w_colors.get(self.world_id, (14,12,22)),
                             (0, 0, self.w, self.h))

        # Rounded border
        border_col = (100, 80, 160) if unlocked else (40, 36, 60)
        if hovered and unlocked:
            border_col = (180, 140, 255)
        pygame.draw.rect(s, border_col, (0, 0, self.w, self.h), 1,
                         border_radius=6)

        wid = self.world_id
        if wid == 0: self._scene_void(s, unlocked, hovered)
        elif wid == 1: self._scene_forest(s, unlocked, hovered)
        elif wid == 2: self._scene_dungeon(s, unlocked, hovered)
        elif wid == 3: self._scene_volcanic(s, unlocked, hovered)
        elif wid == 4: self._scene_astral(s, unlocked, hovered)

        # Dim overlay if locked
        if not unlocked:
            dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 140))
            s.blit(dim, (0, 0))
            # Lock icon
            lx, ly = self.w // 2, self.h // 2
            pygame.draw.rect(s, (80, 70, 100), (lx-7, ly-2, 14, 11), border_radius=2)
            pygame.draw.arc(s, (80, 70, 100),
                            (lx-5, ly-9, 10, 10), 0, math.pi, 2)

        surface.blit(s, (x, y))

    # ---- per-world scenes ----

    def _scene_void(self, s, unlocked, hovered):
        t = self._t
        for sx, sy, br in self._stars[:15]:
            twinkle = max(0, min(255, int(br + math.sin(t * 1.5 + sx) * 25))) if unlocked else br // 3
            pygame.draw.circle(s, (twinkle, twinkle, min(255, twinkle+20)), (sx, sy), 1)
        # Mini tower
        cx, cy = self.w // 2, self.h - 20
        pygame.draw.rect(s, (55, 46, 80) if unlocked else (30,26,40), (cx-7, cy-28, 14, 30))
        for bx in range(cx-7, cx+7, 5):
            pygame.draw.rect(s, (65, 55, 90) if unlocked else (35,30,45), (bx, cy-34, 4, 6))
        if unlocked:
            # Orbiting mote
            mx = cx + int(math.cos(t * 2) * 14)
            my = cy - 28 + int(math.sin(t * 2) * 5)
            pygame.draw.circle(s, (180, 140, 255), (mx, my), 3)

    def _scene_forest(self, s, unlocked, hovered):
        t = self._t
        # Stars
        for sx, sy, br in self._stars[:8]:
            br2 = br // 4 if not unlocked else int(br * 0.4)
            pygame.draw.circle(s, (br2, br2, br2), (sx, sy//2), 1)
        # Ground
        ground_col = (14, 28, 16) if unlocked else (16, 22, 16)
        pygame.draw.rect(s, ground_col, (0, self.h - 18, self.w, 18))
        # Trees
        for tx, ty, th in self._trees:
            trunk_col = (25, 40, 22) if unlocked else (22, 28, 20)
            pygame.draw.rect(s, trunk_col, (tx-2, ty-th//2, 4, th//2))
            canopy_col = (22, 55, 24) if unlocked else (20, 30, 20)
            pygame.draw.circle(s, canopy_col, (tx, ty - th//2), th//2 + 2)
        if unlocked:
            # Firefly
            for fx, fy, phase in self._orbs[:3]:
                glow = int(160 + math.sin(t * 3 + phase) * 80)
                if glow > 100:
                    pygame.draw.circle(s, (glow//3, glow, glow//4), (int(fx), int(fy)), 2)
            # Fog
            for fy in range(self.h - 18, self.h - 8):
                fog_s = pygame.Surface((self.w, 1), pygame.SRCALPHA)
                fog_s.fill((20, 40, 22, int(60 * (fy - (self.h-18)) / 10)))
                s.blit(fog_s, (0, fy))

    def _scene_dungeon(self, s, unlocked, hovered):
        t = self._t
        # Brick floor lines
        line_col = (32, 28, 38) if unlocked else (22, 20, 26)
        for y in range(0, self.h, 10):
            off = (y // 10 % 2) * 12
            for x in range(-12 + off, self.w, 24):
                pygame.draw.rect(s, line_col, (x, y, 22, 9), 1)
        if unlocked:
            # Torch flicker
            for i, tx in enumerate([self.w//4, self.w*3//4]):
                flicker = math.sin(t * 7 + i * 2.1) * 0.3 + 0.7
                pygame.draw.rect(s, (70, 55, 40), (tx-2, 8, 4, 8))
                for fr in range(3, 0, -1):
                    alpha = int(140 * flicker * fr / 3)
                    fs = pygame.Surface((fr*3, fr*4), pygame.SRCALPHA)
                    pygame.draw.ellipse(fs, (220, 120, 20, alpha), (0, 0, fr*3, fr*4))
                    s.blit(fs, (tx - fr*3//2, 4 - fr*4))
        else:
            for tx in [self.w//4, self.w*3//4]:
                pygame.draw.rect(s, (40, 35, 28), (tx-2, 8, 4, 8))

    def _scene_volcanic(self, s, unlocked, hovered):
        t = self._t
        # Lava glow from bottom
        for gy in range(self.h // 2, self.h):
            pct = (gy - self.h//2) / (self.h//2)
            if unlocked:
                flicker = math.sin(t * 2 + gy * 0.1) * 0.15 + 0.85
                r = int(200 * pct * flicker)
                gs = pygame.Surface((self.w, 1), pygame.SRCALPHA)
                gs.fill((r, int(r*0.2), 0, int(80 * pct)))
                s.blit(gs, (0, gy))
            else:
                r = int(60 * pct)
                gs = pygame.Surface((self.w, 1), pygame.SRCALPHA)
                gs.fill((r, 0, 0, int(40 * pct)))
                s.blit(gs, (0, gy))
        # Rocks
        for rx, ry, rs in self._rocks:
            col = (50, 28, 18) if unlocked else (35, 22, 16)
            pygame.draw.ellipse(s, col, (rx-rs, ry-rs//2, rs*2, rs))
        if unlocked:
            # Drifting embers
            for i, (ox, oy, phase) in enumerate(self._orbs[:5]):
                drift_y = (oy - t * 25 * (0.5 + i*0.1)) % self.h
                alpha = int(180 * abs(math.sin(t + phase)))
                if alpha > 60:
                    es = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(es, (255, 120, 0, alpha), (2, 2), 2)
                    s.blit(es, (int(ox), int(drift_y)))

    def _scene_astral(self, s, unlocked, hovered):
        t = self._t
        # Stars with color tint
        for sx, sy, br in self._stars:
            tint = int(abs(math.sin(t * 0.5 + sx * 0.05)) * 40) if unlocked else 0
            if unlocked:
                col = (max(0, br//2 - tint//2), br//2, min(255, br//2 + tint))
            else:
                col = (br//6, br//6, br//5)
            pygame.draw.circle(s, col, (sx, sy), 1)
        if unlocked:
            # Nebula blob
            for i, (ox, oy, phase) in enumerate(self._orbs[:2]):
                r = 20 + int(math.sin(t * 0.4 + phase) * 5)
                nb = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(nb, (60+i*40, 20, 120+i*30, 30), (r, r), r)
                s.blit(nb, (int(ox) - r, int(oy) - r))
            # Floating platform
            px = int(self.w * 0.3 + math.sin(t * 0.4) * 8)
            py = self.h // 2 + 5
            ps = pygame.Surface((40, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(ps, (60, 40, 100, 160), (0, 0, 40, 8))
            s.blit(ps, (px, py))


# ------------------------------------------------------------------ backgrounds

class Background:
    """Drawn-in-code animated background. One instance per run, reused each frame."""

    def __init__(self, world_id, screen_w, screen_h):
        self.world_id = world_id
        self.W        = screen_w
        self.H        = screen_h
        self._t       = 0.0
        self._rng     = random.Random(world_id * 1337)
        self._init_static()

    def _init_static(self):
        """Pre-generate static decoration positions so they don't re-randomise."""
        W, H = self.W, self.H
        rng  = self._rng

        self._stars = [(rng.randint(0, W), rng.randint(0, H),
                        rng.randint(60, 200)) for _ in range(80)]

        # Forest trees
        self._trees = [(rng.randint(20, W-20), rng.randint(H//2, H-20),
                        rng.randint(30, 70)) for _ in range(18)]

        # Dungeon bricks — horizontal lines
        self._bricks = [(rng.randint(0, W), y)
                        for y in range(0, H, 32) for _ in range(W//80)]

        # Volcanic rocks
        self._rocks = [(rng.randint(0, W), rng.randint(H*2//3, H),
                        rng.randint(15, 45)) for _ in range(14)]

        # Embers (positions, will drift upward)
        self._embers = [(rng.uniform(0, W), rng.uniform(0, H),
                         rng.uniform(0.3, 1.0)) for _ in range(40)]

        # Nebula blobs
        self._nebulae = [(rng.randint(50, W-50), rng.randint(50, H-50),
                          rng.randint(60, 160),
                          (rng.randint(60,120), rng.randint(20,80), rng.randint(120,200)))
                         for _ in range(6)]

        # Fireflies
        self._fireflies = [(rng.uniform(0, W), rng.uniform(H//3, H),
                            rng.uniform(0, math.pi*2)) for _ in range(24)]

    def update(self, dt):
        self._t += dt
        # Drift embers upward, wrap
        self._embers = [
            (x, (y - spd * 40 * dt) % self.H, spd)
            for x, y, spd in self._embers
        ]
        # Drift fireflies
        self._fireflies = [
            (x + math.sin(phase + self._t * 0.8) * 0.4,
             y + math.cos(phase * 1.3 + self._t * 0.6) * 0.3,
             phase)
            for x, y, phase in self._fireflies
        ]

    def draw(self, surface):
        w = self.world_id
        if   w == 0: self._draw_void(surface)
        elif w == 1: self._draw_forest(surface)
        elif w == 2: self._draw_dungeon(surface)
        elif w == 3: self._draw_volcanic(surface)
        elif w == 4: self._draw_astral(surface)

    # ---- Void

    def _draw_void(self, surface):
        surface.fill((14, 12, 22))
        for sx, sy, br in self._stars:
            twinkle = max(0, min(255, int(br + math.sin(self._t * 1.2 + sx) * 30)))
            pygame.draw.circle(surface, (twinkle, twinkle, min(255, twinkle+20)),
                               (sx, sy), 1)
        # Distant rune rings drawn by main — nothing extra needed

    # ---- Cursed Forest

    def _draw_forest(self, surface):
        surface.fill((10, 18, 12))
        # Night sky
        for sx, sy, br in self._stars[:30]:
            pygame.draw.circle(surface, (br//2, br//2, br//3), (sx, sy//2), 1)
        # Ground
        pygame.draw.rect(surface, (14, 28, 16),
                         (0, self.H*2//3, self.W, self.H//3))
        # Trees (silhouettes)
        for tx, ty, th in self._trees:
            # Trunk
            pygame.draw.rect(surface, (20, 35, 18),
                             (tx - 5, ty, 10, th//2))
            # Canopy layers
            for j in range(3):
                r = int(th * (0.5 - j*0.12))
                y = ty - j * th//4
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (18+j*4, 45+j*8, 20+j*4, 200),
                                   (r, r), r)
                surface.blit(s, (tx - r, y - r))
        # Fireflies
        for fx, fy, phase in self._fireflies:
            glow = int(180 + math.sin(self._t * 3 + phase) * 75)
            col  = (glow//3, glow, glow//4)
            s    = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, 160), (4, 4), 3)
            surface.blit(s, (int(fx)-4, int(fy)-4))
        # Ground fog
        fog = pygame.Surface((self.W, 60), pygame.SRCALPHA)
        for fy in range(60):
            alpha = int(80 * (1 - fy/60))
            pygame.draw.line(fog, (20, 40, 22, alpha), (0, fy), (self.W, fy))
        surface.blit(fog, (0, self.H*2//3 - 20))

    # ---- Dungeon Depths

    def _draw_dungeon(self, surface):
        surface.fill((16, 14, 20))
        # Stone floor tiles
        for y in range(0, self.H, 32):
            offset = (y // 32 % 2) * 40
            for x in range(-40 + offset, self.W + 40, 80):
                pygame.draw.rect(surface, (28, 26, 32),
                                 (x, y, 78, 30), 1)
        # Torches on walls
        for i, tx in enumerate(range(80, self.W, 200)):
            flicker = math.sin(self._t * 8 + i * 2.1) * 0.3 + 0.7
            # Sconce
            pygame.draw.rect(surface, (60, 50, 40), (tx-4, 30, 8, 16))
            # Flame
            for fr in range(4, 0, -1):
                alpha = int(160 * flicker * fr / 4)
                s = pygame.Surface((fr*4, fr*5), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (220, 120+fr*10, 20, alpha),
                                    (0, 0, fr*4, fr*5))
                surface.blit(s, (tx - fr*2, 14 - fr*5))
            # Light pool
            ls = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(ls, (200, 140, 40, int(20*flicker)),
                               (60, 60), 60)
            surface.blit(ls, (tx - 60, -10))
        # Ceiling drips
        for i, (bx, by) in enumerate(self._bricks[:12]):
            if i % 3 == 0:
                drip_y = int(by + math.sin(self._t*0.5 + i) * 2)
                pygame.draw.line(surface, (40, 36, 50),
                                 (bx, 0), (bx, drip_y + 8), 1)
                pygame.draw.circle(surface, (50, 46, 60), (bx, drip_y + 8), 2)

    # ---- Volcanic Crater

    def _draw_volcanic(self, surface):
        surface.fill((22, 10, 8))
        # Lava glow at bottom
        for gy in range(self.H//2, self.H):
            t   = (gy - self.H//2) / (self.H//2)
            alpha = int(60 * t)
            flicker = math.sin(self._t * 2 + gy * 0.05) * 0.2 + 0.8
            s = pygame.Surface((self.W, 1), pygame.SRCALPHA)
            s.fill((int(200*flicker), int(60*t*flicker), 0, alpha))
            surface.blit(s, (0, gy))
        # Rock silhouettes
        for rx, ry, rs in self._rocks:
            pygame.draw.ellipse(surface, (35, 20, 15),
                                (rx-rs, ry-rs//2, rs*2, rs))
            pygame.draw.ellipse(surface, (50, 30, 20),
                                (rx-rs+4, ry-rs//2+2, rs*2-8, rs-4))
        # Lava cracks
        for i in range(8):
            x = int(self.W * i / 8 + math.sin(self._t * 0.3 + i) * 10)
            glow = int(180 + math.sin(self._t * 2 + i) * 40)
            pygame.draw.line(surface, (glow, glow//4, 0),
                             (x, self.H*3//4), (x + 20, self.H), 2)
        # Drifting embers
        for ex, ey, spd in self._embers:
            alpha = int(200 * spd)
            r     = max(1, int(3 * spd))
            s     = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, int(120*spd), 0, alpha),
                               (r+1, r+1), r)
            surface.blit(s, (int(ex)-r, int(ey)-r))

    # ---- Astral Plane

    def _draw_astral(self, surface):
        surface.fill((8, 8, 24))
        # Nebula blobs
        for nx, ny, nr, nc in self._nebulae:
            pulse = 1.0 + math.sin(self._t * 0.4 + nx) * 0.1
            r     = int(nr * pulse)
            s     = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*nc, 35), (r+1, r+1), r)
            surface.blit(s, (nx-r-1, ny-r-1))
        # Stars — more than void, with color tint
        for sx, sy, br in self._stars:
            phase   = math.sin(self._t * 0.8 + sx * 0.01) * 30
            twinkle = int(br + phase)
            tint    = int(abs(math.sin(self._t*0.2 + sy*0.02)) * 60)
            r = max(0, min(255, twinkle))
            g = max(0, min(255, twinkle - tint//2))
            b = max(0, min(255, twinkle + tint))
            pygame.draw.circle(surface, (r, g, b), (sx, sy), 1)
        # Drifting star clusters
        for i, (ex, ey, spd) in enumerate(self._embers[:20]):
            drift_x = int(ex + math.sin(self._t * 0.2 + i) * 3)
            drift_y = int(ey + math.cos(self._t * 0.15 + i) * 2)
            pygame.draw.circle(surface, (180, 140, 255), (drift_x, drift_y), 1)
        # Floating platforms / astral debris
        for i in range(5):
            px = int(self.W * 0.15 * i + self.W * 0.05 +
                     math.sin(self._t * 0.3 + i * 1.3) * 15)
            py = int(self.H * 0.3 + i * self.H * 0.1 +
                     math.cos(self._t * 0.2 + i) * 8)
            s  = pygame.Surface((80, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (60, 40, 100, 140), (0, 0, 80, 12))
            surface.blit(s, (px, py))
