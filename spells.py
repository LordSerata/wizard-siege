"""
Spell effects for Wizard Siege.

Each spell fires its own distinct projectile on a cooldown, completely
separate from the wizard's regular bolts.
"""

import math
import random
import pygame
from gfx import glow_circle


# ------------------------------------------------------------------ particles

class Particle:
    def __init__(self, pos, vel, color, life, radius=3, fade=True):
        self.pos      = pygame.Vector2(pos)
        self.vel      = pygame.Vector2(vel)
        self.color    = color
        self.life     = life
        self.max_life = life
        self.radius   = radius
        self.fade     = fade
        self.done     = False

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.done = True
            return
        self.vel  *= (1 - dt * 4)
        self.pos  += self.vel * dt

    def draw(self, surface, offset):
        t     = self.life / self.max_life
        alpha = int(255 * t) if self.fade else 255
        r     = max(1, int(self.radius * t))
        s     = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r+1, r+1), r)
        surface.blit(s, (self.pos.x + offset.x - r - 1,
                         self.pos.y + offset.y - r - 1))


def burst(pos, color, count, speed, life, radius=3):
    out = []
    for _ in range(count):
        a   = random.uniform(0, math.pi * 2)
        spd = random.uniform(speed * 0.4, speed)
        out.append(Particle(pos,
                            pygame.Vector2(math.cos(a), math.sin(a)) * spd,
                            color, life, radius))
    return out


# ------------------------------------------------------------------ Fireball

class FireballProjectile:
    TRAIL_COLORS = [(255, 220, 80), (255, 140, 20), (200, 60, 10)]

    def __init__(self, origin, target, damage, radius, chains):
        self.pos     = pygame.Vector2(origin)
        self.target  = target
        self.damage  = damage
        self.radius  = radius
        self.chains  = chains
        self.speed   = 220
        self.done    = False
        self._trail  = []
        self._wobble = random.uniform(0, math.pi * 2)
        heading = target.pos - self.pos
        self.vel = heading.normalize() * self.speed if heading.length() > 0 \
                   else pygame.Vector2(0, -self.speed)

    def update(self, dt, enemies):
        self._wobble += dt * 8
        if self.target and self.target.alive:
            to = self.target.pos - self.pos
            if to.length() > 0:
                self.vel = self.vel.lerp(to.normalize() * self.speed, dt * 3)
        self._trail.append(pygame.Vector2(self.pos))
        if len(self._trail) > 12:
            self._trail.pop(0)
        self.pos += self.vel * dt
        for e in enemies:
            if e.alive and self.pos.distance_to(e.pos) <= self.radius * 0.5 + e.radius:
                self.done = True
                return e
        import settings as cfg
        if not (-80 <= self.pos.x <= cfg.SCREEN_WIDTH + 80 and
                -80 <= self.pos.y <= cfg.SCREEN_HEIGHT + 80):
            self.done = True
        return None

    def draw(self, surface, offset):
        for i, tp in enumerate(self._trail):
            t   = i / max(1, len(self._trail))
            r   = max(1, int(8 * t))
            col = self.TRAIL_COLORS[int(t * (len(self.TRAIL_COLORS) - 1))]
            s   = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, int(180 * t)), (r+1, r+1), r)
            surface.blit(s, (tp.x + offset.x - r - 1, tp.y + offset.y - r - 1))
        drawn = self.pos + offset
        glow_circle(surface, (255, 120, 20), drawn, 14, layers=3, max_alpha=140)
        pygame.draw.circle(surface, (255, 200, 60), drawn, 10)
        pygame.draw.circle(surface, (255, 240, 180), drawn, 5)
        for i in range(4):
            a  = self._wobble + i * math.pi / 2
            sp = drawn + pygame.Vector2(math.cos(a), math.sin(a)) * 12
            pygame.draw.circle(surface, (255, 160, 40), sp, 3)


class FireballSpell:
    COLORS = [(255, 200, 60), (255, 120, 20), (200, 50, 10)]

    def __init__(self, mods):
        self.exp_radius   = 70  + mods.get("radius",   0) * 15
        self.chain_chance = 0.3 + mods.get("chance",   0) * 0.07
        self.damage       = 25  + mods.get("damage",   0) * 8
        self.chains       =       mods.get("chains",   0)
        self._cooldown    = 2.5
        self._timer       = 1.0
        self._projectiles = []
        self._explosions  = []
        self._particles   = []

    def _nearest(self, wizard, enemies):
        best, best_d = None, wizard.range * 1.5
        for e in enemies:
            d = wizard.pos.distance_to(e.pos)
            if d < best_d:
                best, best_d = e, d
        return best

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0 and enemies:
            t = self._nearest(wizard, enemies)
            if t:
                self._projectiles.append(
                    FireballProjectile(wizard.pos, t,
                                       self.damage, self.exp_radius, self.chains))
            self._timer = self._cooldown
        for proj in self._projectiles:
            hit = proj.update(dt, enemies)
            if hit:
                self._explode(hit.pos, enemies, self.chains)
        self._projectiles = [p for p in self._projectiles if not p.done]
        for exp in self._explosions:
            exp[1] -= dt
        self._explosions = [e for e in self._explosions if e[1] > 0]
        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def _explode(self, pos, enemies, chains_left):
        self._explosions.append([pygame.Vector2(pos), 0.45, self.exp_radius])
        self._particles += burst(pos, random.choice(self.COLORS), 24, 200, 0.7, 6)
        for e in enemies:
            if e.pos.distance_to(pos) <= self.exp_radius:
                e.take_damage(self.damage)
                if chains_left > 0 and random.random() < self.chain_chance:
                    self._explode(e.pos, enemies, chains_left - 1)

    def on_kill(self, enemy, enemies):
        if random.random() < self.chain_chance:
            self._explode(enemy.pos, enemies, self.chains)

    def draw(self, surface, offset):
        for proj in self._projectiles:
            proj.draw(surface, offset)
        for pos, timer, radius in self._explosions:
            t = timer / 0.45
            r = int(radius * (1.6 - t * 0.6))
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 140, 20, int(200*t)), (r+2, r+2), r)
            pygame.draw.circle(s, (255, 240, 100, int(100*t)), (r+2, r+2), max(1, r-10))
            surface.blit(s, (pos.x + offset.x - r - 2, pos.y + offset.y - r - 2))
        for p in self._particles:
            p.draw(surface, offset)


# ------------------------------------------------------------------ Ice Lance

class IceLanceProjectile:
    """Fast icy lance — elongated sharp shard."""

    def __init__(self, origin, target, damage, slow_dur, slow_amount,
                 shatter_mul, freeze_chance):
        self.pos           = pygame.Vector2(origin)
        self.target        = target
        self.damage        = damage
        self.slow_dur      = slow_dur
        self.slow_amount   = slow_amount
        self.shatter_mul   = shatter_mul
        self.freeze_chance = freeze_chance
        self.speed         = 480
        self.done          = False
        self._angle        = 0.0
        heading = target.pos - self.pos
        if heading.length() > 0:
            self.vel   = heading.normalize() * self.speed
            self._angle = math.atan2(heading.y, heading.x)
        else:
            self.vel   = pygame.Vector2(0, -self.speed)

    def update(self, dt, enemies):
        self.pos += self.vel * dt
        for e in enemies:
            if e.alive and self.pos.distance_to(e.pos) <= 6 + e.radius:
                self.done = True
                return e
        import settings as cfg
        if not (-80 <= self.pos.x <= cfg.SCREEN_WIDTH + 80 and
                -80 <= self.pos.y <= cfg.SCREEN_HEIGHT + 80):
            self.done = True
        return None

    def draw(self, surface, offset):
        drawn = self.pos + offset
        # Elongated lance shape — rotated polygon
        length, width = 22, 5
        cos_a, sin_a  = math.cos(self._angle), math.sin(self._angle)
        tip  = drawn + pygame.Vector2( cos_a,  sin_a) * length
        tail = drawn + pygame.Vector2(-cos_a, -sin_a) * length * 0.4
        perp = pygame.Vector2(-sin_a, cos_a) * width
        pts  = [tip, tail + perp, tail - perp]
        glow_circle(surface, (140, 220, 255), drawn, 10, layers=2, max_alpha=100)
        pygame.draw.polygon(surface, (200, 240, 255), pts)
        pygame.draw.polygon(surface, (255, 255, 255),
                            [tip,
                             drawn + pygame.Vector2( cos_a,  sin_a) * 6 + perp * 0.3,
                             drawn + pygame.Vector2( cos_a,  sin_a) * 6 - perp * 0.3])


class IceLanceSpell:
    ICE_COLOR = (140, 220, 255)

    def __init__(self, mods):
        self.slow_dur      = 2.0 + mods.get("slow_dur",      0) * 0.5
        self.slow_amount   = 0.4 + mods.get("slow_amount",   0) * 0.06
        self.shatter_mul   = 2.0 + mods.get("shatter_mul",   0) * 0.4
        self.freeze_chance = 0.4 + mods.get("freeze_chance", 0) * 0.06
        self._cooldown     = 1.8
        self._timer        = 0.8
        self._projectiles  = []
        self._particles    = []
        self._shatter_fx   = []

    def _nearest(self, wizard, enemies):
        best, best_d = None, wizard.range * 1.5
        for e in enemies:
            d = wizard.pos.distance_to(e.pos)
            if d < best_d:
                best, best_d = e, d
        return best

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0 and enemies:
            t = self._nearest(wizard, enemies)
            if t:
                self._projectiles.append(
                    IceLanceProjectile(wizard.pos, t, 18,
                                       self.slow_dur, self.slow_amount,
                                       self.shatter_mul, self.freeze_chance))
            self._timer = self._cooldown

        for proj in self._projectiles:
            hit = proj.update(dt, enemies)
            if hit:
                self._on_hit(hit, 18)
        self._projectiles = [p for p in self._projectiles if not p.done]

        # Tick freeze timers
        for e in enemies:
            if getattr(e, "slow_timer", 0) > 0:
                e.slow_timer -= dt
                if e.slow_timer <= 0:
                    e.frozen = False
                    if hasattr(e, "_base_speed"):
                        e.speed = e._base_speed

        for fx in self._shatter_fx:
            fx[1] -= dt
        self._shatter_fx = [f for f in self._shatter_fx if f[1] > 0]
        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def _on_hit(self, enemy, damage):
        if getattr(enemy, "frozen", False):
            enemy.take_damage(int(damage * (self.shatter_mul - 1)))
            self._shatter_fx.append([pygame.Vector2(enemy.pos), 0.45])
            self._particles += burst(enemy.pos, self.ICE_COLOR, 28, 160, 0.55, 5)
            enemy.frozen     = False
            enemy.slow_timer = 0
            if hasattr(enemy, "_base_speed"):
                enemy.speed = enemy._base_speed
        else:
            if random.random() < self.freeze_chance:
                if not hasattr(enemy, "_base_speed"):
                    enemy._base_speed = enemy.speed
                enemy.frozen     = True
                enemy.slow_timer = self.slow_dur
                enemy.speed      = enemy._base_speed * (1 - self.slow_amount)
                self._particles += burst(enemy.pos, self.ICE_COLOR, 14, 90, 0.5, 3)

    def on_bolt_hit(self, enemy, damage, _):
        self._on_hit(enemy, damage)

    def draw(self, surface, offset):
        for proj in self._projectiles:
            proj.draw(surface, offset)
        for pos, timer in self._shatter_fx:
            t = timer / 0.45
            for i in range(6):
                a  = i * math.pi / 3
                r2 = int(28 * (1 - t) + 6)
                ep = pos + offset + pygame.Vector2(math.cos(a), math.sin(a)) * r2
                alpha = int(220 * t)
                s  = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.polygon(s, (200, 240, 255, alpha),
                                    [(4, 0), (7, 6), (1, 6)])
                surface.blit(s, (ep.x - 4, ep.y - 4))
        for p in self._particles:
            p.draw(surface, offset)


# ------------------------------------------------------------------ Zephyr

class WindBladeProjectile:
    """Fast crescent wind blade that pierces through enemies."""

    def __init__(self, origin, direction, damage, push_force):
        self.pos        = pygame.Vector2(origin)
        self.damage     = damage
        self.push_force = push_force
        self.speed      = 520
        self.vel        = direction.normalize() * self.speed
        self._angle     = math.atan2(direction.y, direction.x)
        self.done       = False
        self._hit       = set()
        self._spin      = 0.0

    def update(self, dt, enemies):
        self._spin += dt * 12
        self.pos   += self.vel * dt
        for e in enemies:
            if id(e) in self._hit or not e.alive:
                continue
            if self.pos.distance_to(e.pos) <= 14 + e.radius:
                e.take_damage(self.damage)
                # Push away from origin
                if (e.pos - self.pos).length() > 0:
                    push_dir = (e.pos - self.pos).normalize()
                    e.pos += push_dir * self.push_force * 0.018
                self._hit.add(id(e))
        import settings as cfg
        if not (-80 <= self.pos.x <= cfg.SCREEN_WIDTH + 80 and
                -80 <= self.pos.y <= cfg.SCREEN_HEIGHT + 80):
            self.done = True

    def draw(self, surface, offset):
        drawn = self.pos + offset
        glow_circle(surface, (160, 255, 180), drawn, 12, layers=2, max_alpha=80)
        # Spinning crescent — two overlapping circles
        r    = 12
        cos_s, sin_s = math.cos(self._spin), math.sin(self._spin)
        c1   = drawn + pygame.Vector2(cos_s, sin_s) * 5
        c2   = drawn - pygame.Vector2(cos_s, sin_s) * 5
        pygame.draw.circle(surface, (200, 255, 210), c1, r)
        # Cutout to make crescent
        pygame.draw.circle(surface, (14, 12, 22), c2, r - 4)
        pygame.draw.circle(surface, (160, 255, 180), drawn, 3)


class ZephyrSpell:
    WIND_COLOR = (180, 240, 200)

    def __init__(self, mods):
        self.push_force  = 280 + mods.get("push_force",  0) * 60
        self.push_radius = 110 + mods.get("push_radius", 0) * 20
        self.push_cd     = 1.0 - mods.get("push_cd",     0) * 0.08
        self.push_damage = 8   + mods.get("push_damage", 0) * 4
        self._pulse_timer = 0.0
        self._blade_timer = 0.0
        self._blade_cd    = 1.4
        self._blades      = []
        self._ring_fx     = []
        self._particles   = []

    def update(self, dt, wizard, enemies, _):
        # Periodic push pulse
        self._pulse_timer -= dt
        if self._pulse_timer <= 0:
            self._pulse_timer = max(0.3, self.push_cd)
            self._pulse(wizard, enemies)

        # Fire wind blades toward enemies
        self._blade_timer -= dt
        if self._blade_timer <= 0 and enemies:
            self._blade_timer = self._blade_cd
            self._launch_blades(wizard, enemies)

        for blade in self._blades:
            blade.update(dt, enemies)
        self._blades = [b for b in self._blades if not b.done]
        for ring in self._ring_fx:
            ring[1] -= dt
        self._ring_fx = [r for r in self._ring_fx if r[1] > 0]
        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def _launch_blades(self, wizard, enemies):
        # Fire 3 blades in a spread toward nearest cluster
        angles = [-0.25, 0, 0.25]
        target = min(enemies, key=lambda e: wizard.pos.distance_to(e.pos),
                     default=None)
        if not target:
            return
        base = (target.pos - wizard.pos)
        if base.length() == 0:
            return
        base = base.normalize()
        for da in angles:
            direction = pygame.Vector2(
                base.x * math.cos(da) - base.y * math.sin(da),
                base.x * math.sin(da) + base.y * math.cos(da))
            self._blades.append(
                WindBladeProjectile(wizard.pos, direction,
                                    self.push_damage, self.push_force))

    def _pulse(self, wizard, enemies):
        self._ring_fx.append([wizard.pos.copy(), self.push_radius, 0.5, 0.5])
        for e in enemies:
            dist = wizard.pos.distance_to(e.pos)
            if dist <= self.push_radius and dist > 0:
                direction = (e.pos - wizard.pos).normalize()
                e.pos += direction * self.push_force * 0.014
                e.take_damage(self.push_damage // 2)
                self._particles += burst(e.pos, self.WIND_COLOR, 5, 80, 0.3, 2)

    def draw(self, surface, offset):
        for blade in self._blades:
            blade.draw(surface, offset)
        for wpos, radius, timer, max_t in self._ring_fx:
            t   = timer / max_t
            r   = int(radius * (1.3 - t * 0.3))
            s   = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (160, 255, 180, int(150*t)), (r+2, r+2), r, 3)
            wx  = int(wpos.x + offset.x)
            wy  = int(wpos.y + offset.y)
            surface.blit(s, (wx - r - 2, wy - r - 2))
        for p in self._particles:
            p.draw(surface, offset)


# ------------------------------------------------------------------ Stone Wall

class StoneWallSpell:
    STONE_COLOR  = (160, 140, 110)
    STONE_BROKEN = (100, 90, 70)
    ORBIT        = 58

    def __init__(self, mods):
        self.stone_hp    = 40  + mods.get("stone_hp",    0) * 15
        self.stone_count = 3   + mods.get("stone_count", 0)
        self.spawn_cd    = 8.0 - mods.get("spawn_cd",    0) * 0.6
        self.contact_dmg = 15  + mods.get("contact_dmg", 0) * 6
        self._spawn_timer = 1.0
        self._stones      = []
        self._particles   = []
        self._spin        = 0.0

    def update(self, dt, wizard, enemies, _):
        self._spin = (self._spin + dt * 1.1) % (math.pi * 2)
        self._spawn_timer -= dt
        if self._spawn_timer <= 0 and len(self._stones) < self.stone_count:
            self._spawn_timer = max(0.5, self.spawn_cd / self.stone_count)
            base_angle = (math.pi * 2 / self.stone_count) * len(self._stones)
            self._stones.append({"angle": base_angle, "hp": self.stone_hp,
                                  "contact_cd": 0.0, "impact_flash": 0.0})

        broken = []
        for stone in self._stones:
            stone["contact_cd"]  -= dt
            stone["impact_flash"] = max(0.0, stone["impact_flash"] - dt * 4)
            sx   = wizard.pos.x + math.cos(stone["angle"] + self._spin) * self.ORBIT
            sy   = wizard.pos.y + math.sin(stone["angle"] + self._spin) * self.ORBIT
            spos = pygame.Vector2(sx, sy)

            for e in enemies:
                if e.pos.distance_to(spos) <= 16 + e.radius:
                    if stone["contact_cd"] <= 0:
                        e.take_damage(self.contact_dmg)
                        stone["hp"]           -= 10
                        stone["contact_cd"]    = 0.4
                        stone["impact_flash"]  = 1.0
                        self._particles += burst(spos, self.STONE_COLOR, 10, 100, 0.45, 3)
            if stone["hp"] <= 0:
                broken.append(stone)
                self._particles += burst(spos, self.STONE_BROKEN, 20, 130, 0.65, 5)

        for b in broken:
            self._stones.remove(b)
        if not self._stones and self._spawn_timer > 1.0:
            self._spawn_timer = 1.0

        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, wizard_pos, offset):
        for stone in self._stones:
            sx   = wizard_pos.x + math.cos(stone["angle"] + self._spin) * self.ORBIT
            sy   = wizard_pos.y + math.sin(stone["angle"] + self._spin) * self.ORBIT
            spos = pygame.Vector2(sx + offset.x, sy + offset.y)
            hp_t = max(0.0, stone["hp"] / self.stone_hp)
            flash = stone["impact_flash"]

            if flash > 0:
                color = tuple(min(255, int(c + (255-c)*flash))
                              for c in self.STONE_COLOR)
            else:
                color = tuple(int(a*hp_t + b*(1-hp_t))
                              for a, b in zip(self.STONE_COLOR, self.STONE_BROKEN))

            glow_circle(surface, color, spos, 16, layers=2, max_alpha=70)

            # Irregular stone shape — octagon with noise
            pts = []
            for i in range(8):
                a    = i * math.pi / 4 + stone["angle"]
                wobble = 1.0 + (math.sin(a * 3 + stone["angle"] * 7) * 0.2)
                r    = int(12 * wobble)
                pts.append((spos.x + math.cos(a)*r, spos.y + math.sin(a)*r))
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (200, 180, 140), pts, 1)
            # Inner highlight
            pts2 = []
            for i in range(8):
                a = i * math.pi / 4 + stone["angle"]
                pts2.append((spos.x + math.cos(a)*6, spos.y + math.sin(a)*6))
            pygame.draw.polygon(surface, (210, 195, 165), pts2)

            # Crack lines when damaged
            if hp_t < 0.7:
                cracks = int((1 - hp_t) * 5) + 1
                for i in range(cracks):
                    a  = stone["angle"] + i * 1.3
                    p1 = spos + pygame.Vector2(math.cos(a), math.sin(a)) * 3
                    p2 = spos + pygame.Vector2(math.cos(a), math.sin(a)) * 12
                    pygame.draw.line(surface, (50, 40, 30), p1, p2, 1)

        for p in self._particles:
            p.draw(surface, pygame.Vector2(0, 0))


# ------------------------------------------------------------------ Engine

class SpellEngine:
    """Owns all active spell instances and routes game events to them."""

    def __init__(self, wizard, run_data):
        self._spells  = {}
        self._hybrids = {}
        owned   = run_data.get("spells_owned",  [])
        hybrids = run_data.get("hybrids_owned", [])
        mods    = run_data.get("spell_mods", {})

        if "fireball"   in owned:
            self._spells["fireball"]   = FireballSpell(mods.get("fireball",   {}))
        if "ice_lance"  in owned:
            self._spells["ice_lance"]  = IceLanceSpell(mods.get("ice_lance",  {}))
        if "zephyr"     in owned:
            self._spells["zephyr"]     = ZephyrSpell(mods.get("zephyr",       {}))
        if "stone_wall" in owned:
            self._spells["stone_wall"] = StoneWallSpell(mods.get("stone_wall",{}))

        for hid in hybrids:
            cls = _HYBRID_CLASSES.get(hid)
            if cls:
                self._hybrids[hid] = cls(mods.get(hid, {}))

        self._wizard = wizard

    def on_kill(self, enemy, enemies):
        for spell in self._spells.values():
            if hasattr(spell, "on_kill"):
                spell.on_kill(enemy, enemies)

    def on_bolt_hit(self, enemy, damage):
        for spell in self._spells.values():
            if hasattr(spell, "on_bolt_hit"):
                spell.on_bolt_hit(enemy, damage, [])

    def update(self, dt, enemies):
        for spell in self._spells.values():
            spell.update(dt, self._wizard, enemies, [])
        for spell in self._hybrids.values():
            spell.update(dt, self._wizard, enemies, [])

    def draw(self, surface, offset):
        for key, spell in self._spells.items():
            if key == "stone_wall":
                spell.draw(surface, self._wizard.pos, offset)
            else:
                spell.draw(surface, offset)
        for key, spell in self._hybrids.items():
            if key == "arcane_singularity":
                spell.draw(surface, offset)
                spell.draw_charge_ring(surface, self._wizard.pos, offset)
            else:
                spell.draw(surface, offset)


# ================================================================ Hybrid Spells

# ---------------------------------------------------------------- Ring 2

class SteamBurstSpell:
    """Fireball + Ice Lance: scalding cloud on a timer that slows and burns."""
    def __init__(self, mods={}):
        self._cloud_radius = 80  + mods.get("cloud_size",  0) * 15
        self._cloud_dur    = 2.5 + mods.get("cloud_dur",   0) * 0.5
        self._burn_dmg     = 4   + mods.get("burn_dmg",    0) * 2
        self._slow         = 0.5 + mods.get("slow_power",  0) * 0.05
        self._timer   = 0.0
        self._cd      = 3.0
        self._clouds  = []
        self._particles = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0:
            self._timer = self._cd
            self._clouds.append([pygame.Vector2(wizard.pos),
                                  self._cloud_radius, self._cloud_dur])

        for cloud in self._clouds:
            cloud[2] -= dt
            for e in enemies:
                if e.pos.distance_to(cloud[0]) <= cloud[1]:
                    e.take_damage(self._burn_dmg * dt)
                    if not hasattr(e, "_base_speed"):
                        e._base_speed = e.speed
                    e.speed = max(e._base_speed * (1 - self._slow),
                                  e.speed - 20 * dt)
            if random.random() < 0.3:
                self._particles += burst(
                    cloud[0] + pygame.Vector2(
                        random.uniform(-cloud[1], cloud[1]),
                        random.uniform(-cloud[1], cloud[1])),
                    (200, 200, 80), 2, 30, 0.5, 3)

        self._clouds = [c for c in self._clouds if c[2] > 0]
        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for pos, radius, timer in self._clouds:
            t = min(1.0, timer / self._cloud_dur)
            r = int(radius)
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 200, 80, max(0, min(255, int(60 * t)))),
                               (r+1, r+1), r)
            surface.blit(s, (pos.x + offset.x - r - 1,
                              pos.y + offset.y - r - 1))
        for p in self._particles: p.draw(surface, offset)


class BlizzardSpell:
    """Ice Lance + Zephyr: wind scatters ice shards in all directions."""
    def __init__(self, mods={}):
        self._shard_count  = 8   + mods.get("shard_count",  0) * 2
        self._shard_dmg    = 12  + mods.get("shard_dmg",    0) * 5
        self._shard_speed  = 480 + mods.get("shard_speed",  0) * 60
        self._freeze_dur   = 1.5 + mods.get("freeze_dur",   0) * 0.4
        self._timer = 0.0
        self._cd    = 2.5
        self._shards = []
        self._particles = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0 and enemies:
            self._timer = self._cd
            for i in range(self._shard_count):
                a = i * math.pi * 2 / self._shard_count
                direction = pygame.Vector2(math.cos(a), math.sin(a))
                class FakeTarget:
                    def __init__(self, pos): self.pos = pos; self.alive = True
                fake = FakeTarget(wizard.pos + direction * 600)
                self._shards.append(
                    IceLanceProjectile(wizard.pos, fake, self._shard_dmg,
                                       self._freeze_dur, 0.5, 1.8, 0.6))

        for shard in self._shards:
            hit = shard.update(dt, enemies)
            if hit:
                self._particles += burst(hit.pos, (140, 220, 255), 8, 80, 0.4, 3)
        self._shards = [s for s in self._shards if not s.done]
        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for shard in self._shards: shard.draw(surface, offset)
        for p in self._particles: p.draw(surface, offset)


class LandslideSpell:
    """Zephyr + Stone Wall: wind hurls stones as fast projectiles."""
    def __init__(self, mods={}):
        self._stone_count = 3   + mods.get("stone_count", 0)
        self._stone_dmg   = 30  + mods.get("stone_dmg",   0) * 10
        self._cd          = 2.0 - mods.get("cooldown",    0) * 0.2
        self._timer = 0.0
        self._bolts = []
        self._particles = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0 and enemies:
            self._timer = max(0.3, self._cd)
            targets = sorted(enemies,
                             key=lambda e: wizard.pos.distance_to(e.pos))[:self._stone_count]
            for target in targets:
                self._bolts.append(
                    FireballProjectile(wizard.pos, target, self._stone_dmg, 40, 0))
        for b in self._bolts:
            hit = b.update(dt, enemies)
            if hit:
                self._particles += burst(hit.pos, (180, 160, 120), 12, 100, 0.5, 4)
        self._bolts = [b for b in self._bolts if not b.done]
        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for b in self._bolts:
            drawn = b.pos + offset
            pygame.draw.circle(surface, (180, 160, 120), drawn, 9)
            pygame.draw.circle(surface, (220, 200, 160), drawn, 5)
        for p in self._particles: p.draw(surface, offset)


class VolcanicBarrageSpell:
    """Stone Wall + Fireball: stones erupt with lava on impact."""
    def __init__(self, mods={}):
        self._lava_radius = 60  + mods.get("lava_radius",  0) * 10
        self._lava_dmg    = 18  + mods.get("lava_dmg",     0) * 8
        self._cd          = 1.8 - mods.get("fire_rate",    0) * 0.2
        self._chains      =       mods.get("chain_lava",   0)
        self._timer = 0.0
        self._bolts = []
        self._explosions = []
        self._particles  = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0 and enemies:
            self._timer = max(0.3, self._cd)
            target = min(enemies, key=lambda e: wizard.pos.distance_to(e.pos),
                         default=None)
            if target:
                self._bolts.append(
                    FireballProjectile(wizard.pos, target, self._lava_dmg,
                                       self._lava_radius, self._chains))

        for b in self._bolts:
            hit = b.update(dt, enemies)
            if hit:
                self._explosions.append([pygame.Vector2(hit.pos), 0.5,
                                          self._lava_radius])
                self._particles += burst(hit.pos, (220, 100, 30), 20, 180, 0.6, 5)
                for e in enemies:
                    if e.pos.distance_to(hit.pos) <= self._lava_radius:
                        e.take_damage(self._lava_dmg)
        self._bolts = [b for b in self._bolts if not b.done]
        for exp in self._explosions: exp[1] -= dt
        self._explosions = [e for e in self._explosions if e[1] > 0]
        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for b in self._bolts:
            drawn = b.pos + offset
            glow_circle(surface, (220, 100, 30), drawn, 12, layers=2, max_alpha=120)
            pygame.draw.circle(surface, (220, 100, 30), drawn, 9)
            pygame.draw.circle(surface, (255, 200, 80), drawn, 5)
        for pos, timer, radius in self._explosions:
            t = timer / 0.5
            r = int(radius * (1.4 - t * 0.4))
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (220, 100, 30, int(180*t)), (r+2, r+2), r)
            surface.blit(s, (pos.x+offset.x-r-2, pos.y+offset.y-r-2))
        for p in self._particles: p.draw(surface, offset)


# ---------------------------------------------------------------- Ring 3

class MaelstromSpell:
    """Steam Burst + Blizzard: swirling storm of ice and steam."""
    def __init__(self, mods={}):
        self._storm_radius = 200 + mods.get("storm_radius", 0) * 20
        self._storm_dmg    = 8   + mods.get("storm_dmg",    0) * 4
        self._slow         = 0.4 + mods.get("slow_power",   0) * 0.08
        self._cd           = 0.15 - mods.get("cooldown",    0) * 0.001
        self._angle = 0.0
        self._particles = []
        self._timer = 0.0

    def update(self, dt, wizard, enemies, _):
        self._angle = (self._angle + dt * 2.5) % (math.pi * 2)
        self._timer -= dt
        if self._timer <= 0:
            self._timer = max(0.05, self._cd)
            for e in enemies:
                dist = wizard.pos.distance_to(e.pos)
                if 60 < dist < self._storm_radius:
                    e.take_damage(self._storm_dmg * dt * 6)
                    if not hasattr(e, "_base_speed"):
                        e._base_speed = e.speed
                    e.speed = max(e._base_speed * (1 - self._slow),
                                  e.speed - 15 * dt * 6)
            # Spiral particles
            for i in range(3):
                a = self._angle + i * math.pi * 2 / 3
                for r in [80, 130, 180]:
                    px = wizard.pos.x + math.cos(a + r * 0.01) * r
                    py = wizard.pos.y + math.sin(a + r * 0.01) * r
                    col = (140, 220, 255) if i % 2 == 0 else (200, 200, 80)
                    self._particles.append(Particle(
                        (px, py),
                        pygame.Vector2(math.cos(a + math.pi/2),
                                       math.sin(a + math.pi/2)) * 40,
                        col, 0.6, 4))

        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for p in self._particles: p.draw(surface, offset)


class AvalancheSpell:
    """Blizzard + Landslide: frozen boulder wave."""
    def __init__(self, mods={}):
        self._boulder_count = 5   + mods.get("boulder_count", 0) * 2
        self._boulder_dmg   = 35  + mods.get("boulder_dmg",   0) * 15
        self._slow          = 0.3 + mods.get("slow_power",    0) * 0.1
        self._cd            = 4.0 - mods.get("cooldown",      0) * 0.5
        self._timer    = 0.0
        self._boulders = []
        self._particles = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0:
            self._timer = max(0.5, self._cd)
            for i in range(self._boulder_count):
                a = -math.pi/4 + i * math.pi / 8
                if enemies:
                    base = (min(enemies,
                                key=lambda e: wizard.pos.distance_to(e.pos))
                            .pos - wizard.pos)
                    if base.length() > 0:
                        base = base.normalize()
                    a2 = math.atan2(base.y, base.x) + a - math.pi/4
                else:
                    a2 = a
                vel = pygame.Vector2(math.cos(a2), math.sin(a2)) * 300
                self._boulders.append([pygame.Vector2(wizard.pos), vel, 80, 0.0])

        survivors = []
        for b in self._boulders:
            b[0] += b[1] * dt
            b[3] -= dt
            for e in enemies:
                if e.pos.distance_to(b[0]) <= 22 + e.radius:
                    e.take_damage(self._boulder_dmg)
                    if not hasattr(e, "_base_speed"):
                        e._base_speed = e.speed
                    e.speed = e._base_speed * (1 - self._slow)
                    b[2] -= 20
                    self._particles += burst(b[0], (180, 220, 255), 8, 100, 0.5, 4)
            import settings as cfg2
            if (b[2] > 0 and
                    -100 <= b[0].x <= cfg2.SCREEN_WIDTH+100 and
                    -100 <= b[0].y <= cfg2.SCREEN_HEIGHT+100):
                survivors.append(b)
            else:
                self._particles += burst(b[0], (180, 220, 255), 16, 140, 0.6, 5)
        self._boulders = survivors

        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for pos, vel, hp, _ in self._boulders:
            drawn = pos + offset
            glow_circle(surface, (180, 220, 255), drawn, 18, layers=2, max_alpha=80)
            pygame.draw.circle(surface, (160, 200, 240), drawn, 14)
            pygame.draw.circle(surface, (200, 230, 255), drawn, 8)
        for p in self._particles: p.draw(surface, offset)


class EarthquakeSpell:
    """Landslide + Volcanic Barrage: ground shockwave."""
    def __init__(self, mods={}):
        self._wave_radius = 350 + mods.get("wave_radius", 0) * 40
        self._wave_dmg    = 40  + mods.get("wave_dmg",    0) * 15
        self._wave_count  = 1   + mods.get("wave_count",  0)
        self._cd          = 5.0 - mods.get("cooldown",    0) * 0.6
        self._timer  = 0.0
        self._waves  = []
        self._particles = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0:
            self._timer = max(0.5, self._cd)
            for _ in range(self._wave_count):
                self._waves.append([pygame.Vector2(wizard.pos), 0,
                                     self._wave_radius, 1.2])

        survivors = []
        for w in self._waves:
            w[3] -= dt
            w[1] = w[2] * (1 - w[3] / 1.2)
            for e in enemies:
                dist = e.pos.distance_to(w[0])
                if abs(dist - w[1]) < 30:
                    e.take_damage(self._wave_dmg)
                    if not hasattr(e, "_base_speed"):
                        e._base_speed = e.speed
                    e.speed = e._base_speed * 0.2
                    self._particles += burst(e.pos, (160, 130, 80), 4, 60, 0.4, 3)
            if w[3] > 0:
                survivors.append(w)
        self._waves = survivors

        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for pos, radius, _, timer in self._waves:
            t = timer / 1.2
            r = int(radius)
            if r <= 0: continue
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (160, 130, 80, int(180 * t)),
                               (r+2, r+2), r, int(12 * t) + 2)
            surface.blit(s, (pos.x+offset.x-r-2, pos.y+offset.y-r-2))
        for p in self._particles: p.draw(surface, offset)


class InfernoSpell:
    """Volcanic Barrage + Steam Burst: persistent growing fire field."""
    def __init__(self, mods={}):
        self._max_radius  = 180 + mods.get("field_size",   0) * 20
        self._burn_dmg    = 12  + mods.get("burn_dmg",     0) * 4
        self._field_dur   = 5.0 + mods.get("field_dur",    0) * 1.0
        self._field_count = 1   + mods.get("field_count",  0)
        self._cd          = 6.0 / max(1, self._field_count)
        self._timer  = 0.0
        self._fields = []
        self._particles = []

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        if self._timer <= 0:
            self._timer = max(0.5, self._cd)
            self._fields.append([pygame.Vector2(wizard.pos), 40,
                                  self._max_radius, self._field_dur, 0.0])

        for f in self._fields:
            f[3] -= dt
            f[4] -= dt
            if f[4] <= 0 and f[1] < f[2]:
                f[1] = min(f[2], f[1] + 15)
                f[4] = 0.5
            for e in enemies:
                if e.pos.distance_to(f[0]) <= f[1]:
                    e.take_damage(self._burn_dmg * dt)
            if random.random() < 0.4:
                angle = random.uniform(0, math.pi * 2)
                r = random.uniform(0, f[1])
                self._particles.append(Particle(
                    (f[0].x + math.cos(angle)*r, f[0].y + math.sin(angle)*r),
                    pygame.Vector2(random.uniform(-20, 20),
                                   random.uniform(-60, -20)),
                    (255, int(80 + random.random()*80), 0), 0.6, 4))

        self._fields = [f for f in self._fields if f[3] > 0]
        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for pos, radius, _, timer, _ in self._fields:
            t = min(1.0, timer / self._field_dur)
            r = int(radius)
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 80, 0, int(50 * t)), (r+1, r+1), r)
            surface.blit(s, (pos.x+offset.x-r-1, pos.y+offset.y-r-1))
        for p in self._particles: p.draw(surface, offset)


# ---------------------------------------------------------------- Ring 4 — Ultimate

class ArcaneSingularitySpell:
    """All 4 ring-3 spells: gravitational pull then massive detonation."""
    def __init__(self, mods={}):
        self._pull_force  = 180 + mods.get("pull_force", 0) * 40
        self._blast_dmg   = 200 + mods.get("blast_dmg",  0) * 50
        self._pull_dur    = 2.5 + mods.get("pull_dur",   0) * 0.5
        self._cd          = 12.0 - mods.get("cooldown",  0) * 1.0
        self._timer  = 0.0
        self._phase  = "idle"
        self._p_timer = 0.0
        self._particles = []
        self._spin   = 0.0

    def update(self, dt, wizard, enemies, _):
        self._timer -= dt
        self._spin  = (self._spin + dt * 3.0) % (math.pi * 2)

        if self._phase == "idle" and self._timer <= 0:
            self._phase   = "pulling"
            self._p_timer = self._pull_dur

        if self._phase == "pulling":
            self._p_timer -= dt
            for e in enemies:
                toward = wizard.pos - e.pos
                if toward.length() > 0:
                    e.pos += toward.normalize() * self._pull_force * dt
            # Spiral particles
            for i in range(6):
                a = self._spin + i * math.pi / 3
                r = 150 + math.sin(self._p_timer * 3) * 30
                self._particles.append(Particle(
                    (wizard.pos.x + math.cos(a)*r,
                     wizard.pos.y + math.sin(a)*r),
                    pygame.Vector2(-math.cos(a), -math.sin(a)) * 120,
                    (220, 160, 255), 0.5, 5))
            if self._p_timer <= 0:
                self._phase   = "exploding"
                self._p_timer = 0.6
                for e in enemies:
                    e.take_damage(self._blast_dmg)
                self._particles += burst(wizard.pos, (220, 160, 255),
                                          60, 300, 1.0, 8)

        if self._phase == "exploding":
            self._p_timer -= dt
            if self._p_timer <= 0:
                self._phase = "idle"
                self._timer = max(3.0, self._cd)

        for p in self._particles: p.update(dt)
        self._particles = [p for p in self._particles if not p.done]

    def draw(self, surface, offset):
        for p in self._particles: p.draw(surface, offset)

    def draw_charge_ring(self, surface, wizard_pos, offset):
        """Extra visual — pulsing ring shown while pulling."""
        if self._phase != "pulling":
            return
        t = min(1.0, self._p_timer / self._pull_dur)
        r = int(160 * t)
        if r <= 0: return
        s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(s, (220, 160, 255, int(140 * t)),
                           (r+2, r+2), r, int(8 * t) + 2)
        wp = wizard_pos + offset
        surface.blit(s, (int(wp.x)-r-2, int(wp.y)-r-2))


# ---------------------------------------------------------------- Engine update

# Append to SpellEngine to handle hybrids
_HYBRID_CLASSES = {
    "steam_burst":        SteamBurstSpell,
    "blizzard":           BlizzardSpell,
    "landslide":          LandslideSpell,
    "volcanic_barrage":   VolcanicBarrageSpell,
    "maelstrom":          MaelstromSpell,
    "avalanche":          AvalancheSpell,
    "earthquake":         EarthquakeSpell,
    "inferno":            InfernoSpell,
    "arcane_singularity": ArcaneSingularitySpell,
}
