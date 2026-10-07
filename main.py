import sys
import math
import random

import pygame

import settings as cfg
import upgrades as up
import run_data as rd
from boss import Boss
from effects import DamageNumber, ScreenShake
from gfx import glow_circle, glow_rect, radial_gradient, load_fonts
from spells import SpellEngine
from player import Wizard
from waves import Spawner
from worlds import WORLDS, get_world, is_unlocked, Background, WorldPreview
import hybrid_tree as ht

# --- States ---
TITLE       = "title"
LABORATORY  = "laboratory"
PLAYING     = "playing"


# ------------------------------------------------------------------ title anim

class TitleEnemy:
    """Simple animated enemy that walks toward the tower on the title screen."""
    SHAPES = {
        "goblin":      ("circle",   (110, 180, 90),  13),
        "wraith":      ("triangle", (150, 200, 235), 10),
        "ogre":        ("square",   (190, 110, 70),  22),
        "revenant":    ("circle",   (200, 90, 200),  17),
        "thornling":   ("triangle", (80, 160, 60),   12),
        "shade":       ("triangle", (40, 60, 80),    9),
        "gargoyle":    ("square",   (100, 95, 120),  20),
        "bone_knight": ("square",   (220, 215, 190), 16),
        "magma_brute": ("square",   (200, 80, 20),   24),
        "cinder_wisp": ("circle",   (255, 140, 40),  8),
        "void_stalker":("triangle", (140, 80, 255),  14),
        "rift_horror": ("circle",   (80, 20, 140),   26),
    }

    def __init__(self, kind, x, y, direction, speed):
        self.kind      = kind
        self.x         = float(x)
        self.y         = float(y)
        self.dir       = direction   # -1 = left, +1 = right (toward center)
        self.speed     = speed
        self.flash     = 0.0
        self.dead      = False
        self.done      = False       # faded out, remove
        self._wobble   = random.uniform(0, math.pi * 2)
        shape, color, radius = self.SHAPES.get(kind, ("circle", (180,180,180), 12))
        self.shape  = shape
        self.color  = color
        self.radius = radius

    def update(self, dt, tower_x):
        self._wobble += dt * 4
        if self.dead:
            self.flash = max(0.0, self.flash - dt * 3)
            self.done  = self.flash <= 0
            return
        self.x += self.speed * self.dir * dt
        # Die when reaching the tower
        dist = abs(self.x - tower_x)
        if dist < 30 + self.radius:
            self.dead  = True
            self.flash = 1.0

    def draw(self, surface, offset_x=0):
        col = (255, 255, 255) if self.flash > 0.7 else self.color
        alpha = int(255 * self.flash) if self.dead else 255
        x, y = int(self.x + offset_x), int(self.y)
        r = self.radius

        s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        if self.shape == "circle":
            pygame.draw.circle(s, (*col, alpha), (r+1, r+1), r)
        elif self.shape == "triangle":
            pts = [(r+1, 1), (1, r*2+1), (r*2+1, r*2+1)]
            pygame.draw.polygon(s, (*col, alpha), pts)
        else:  # square
            pygame.draw.rect(s, (*col, alpha), (1, 1, r*2, r*2), border_radius=3)
        surface.blit(s, (x - r - 1, y - r - 1))


class TitleBolt:
    """Quick bolt that flies from tower toward a target x."""
    def __init__(self, sx, sy, tx, ty):
        self.pos  = pygame.Vector2(sx, sy)
        heading   = pygame.Vector2(tx - sx, ty - sy)
        self.vel  = heading.normalize() * 500 if heading.length() > 0 \
                    else pygame.Vector2(1, 0)
        self.done = False
        self.life = 0.4

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0:
            self.done = True

    def draw(self, surface):
        pygame.draw.circle(surface, (180, 140, 255), self.pos, 4)
        pygame.draw.circle(surface, (255, 255, 255), self.pos, 2)
BOSS_FIGHT  = "boss_fight"
DEAD        = "dead"
PAUSED      = "paused"

SHOP_KEYS = list(up.SHOP_UPGRADES.keys())
MAX_UPGRADE = 100


def kills_for_level(level):
    return cfg.LEVEL_KILLS_BASE + (level - 1) * cfg.LEVEL_KILLS_GROWTH


def difficulty_for_level(level):
    return 1.0 + (level - 1) * cfg.DIFF_HP_FACTOR


# ------------------------------------------------------------------ helpers

def draw_rect_alpha(surface, color, rect, alpha, radius=0):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0, 0, rect.width, rect.height),
                     border_radius=radius)
    surface.blit(s, rect.topleft)


class Button:
    """Simple text button with hover highlight."""
    def __init__(self, rect, text, font,
                 color=(235, 233, 245), hover=(180, 150, 255),
                 bg=(32, 28, 50), border=(110, 90, 180)):
        self.rect   = pygame.Rect(rect)
        self.text   = text
        self.font   = font
        self.color  = color
        self.hover  = hover
        self.bg     = bg
        self.border = border

    # Class-level slot updated by Game before drawing
    _canvas_offset = (0, 0)
    _canvas_scale  = 1.0

    def draw(self, surface):
        raw = pygame.mouse.get_pos()
        ox, oy = Button._canvas_offset
        scale  = Button._canvas_scale
        if scale > 0:
            mx = (raw[0] - ox) / scale
            my = (raw[1] - oy) / scale
        else:
            mx, my = raw
        hovered = self.rect.collidepoint(mx, my)
        bg = tuple(min(255, c + 20) for c in self.bg) if hovered else self.bg
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border, self.rect, 2, border_radius=8)
        label = self.font.render(
            self.text, True, self.hover if hovered else self.color)
        # Center on visual glyph height (ascent), not the full surface which
        # includes empty descender space that pushes text up visually.
        ascent = self.font.get_ascent()
        descent = abs(self.font.get_descent())
        visual_height = ascent + descent
        top = self.rect.centery - visual_height // 2 + descent // 2
        r = label.get_rect()
        r.centerx = self.rect.centerx
        r.top = top
        surface.blit(label, r)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))

    def clicked_pos(self, pos):
        return self.rect.collidepoint(pos)


# ============================================================== Game class

class Game:
    def __init__(self):
        pygame.init()
        self._fullscreen = False
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption(cfg.CAPTION)
        # Fixed-size canvas — all drawing goes here, then scaled to display
        self.canvas = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        self.clock      = pygame.time.Clock()

        import os
        fonts = load_fonts(os.path.dirname(__file__))
        self.font       = fonts["ui"]
        self.small_font = fonts["ui_sm"]
        self.big_font   = fonts["title"]
        self.med_font   = fonts["heading"]
        self.tiny_font  = fonts["ui_xs"]

        self.run_data   = rd.load()
        self.lab_tab    = "permanent"
        self.lab_spell  = None
        self._bg        = Background(self.run_data.get("current_world", 0),
                                     cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
        self._build_title_buttons()
        self._build_lab_buttons()
        self.state = TITLE
        self._title_spin = 0.0
        self._title_enemies = []   # list of TitleEnemy
        self._title_spawn_t = 0.0
        self._title_bolts   = []   # list of TitleBolt

    # ---------------------------------------------------------------- buttons

    def _update_title_enemies(self, dt):
        W, H = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        cx   = W // 2
        # Tower base is at roughly y=350 (ty=220, th=130 → ground_y=350)
        ground_y = 350
        tower_x  = cx

        # Spawn new enemies
        self._title_spawn_t -= dt
        if self._title_spawn_t <= 0:
            self._title_spawn_t = random.uniform(0.8, 1.8)
            world_id = self.run_data.get("current_world", 0)
            wdata    = get_world(world_id)
            kind     = random.choice(wdata["enemies"])
            side     = random.choice((-1, 1))
            start_x  = cx + side * random.randint(280, 480)
            speed    = random.uniform(55, 95)
            shape_data = TitleEnemy.SHAPES.get(kind, ("circle",(180,180,180),12))
            r        = shape_data[2]
            y        = ground_y - r
            self._title_enemies.append(
                TitleEnemy(kind, start_x, y, -side, speed))

        # Update enemies; fire a bolt when one gets close
        for e in self._title_enemies:
            e.update(dt, tower_x)
            if not e.dead and abs(e.x - tower_x) < 120 + e.radius:
                # Fire bolt from tower tip
                tip_y = 220 - 8
                self._title_bolts.append(
                    TitleBolt(tower_x, tip_y, e.x, e.y))
                e.dead  = True
                e.flash = 1.0

        for b in self._title_bolts:
            b.update(dt)

        self._title_enemies = [e for e in self._title_enemies if not e.done]
        self._title_bolts   = [b for b in self._title_bolts if not b.done]

        # Reset spawn state when world changes
        cur = self.run_data.get("current_world", 0)
        if not hasattr(self, "_title_last_world") or self._title_last_world != cur:
            self._title_enemies.clear()
            self._title_bolts.clear()
            self._title_spawn_t = 0
            self._title_last_world = cur

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(
                (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.RESIZABLE)

    @property
    def W(self):
        return self.screen.get_width()

    @property
    def H(self):
        return self.screen.get_height()

    def _to_canvas(self, pos):
        """Remap a display-space mouse position to canvas space."""
        ox = getattr(self, "_display_offset", (0, 0))[0]
        oy = getattr(self, "_display_offset", (0, 0))[1]
        scale = getattr(self, "_display_scale", 1.0)
        if scale == 0:
            return pos
        return ((pos[0] - ox) / scale, (pos[1] - oy) / scale)

    def _build_title_buttons(self):
        cx = cfg.SCREEN_WIDTH // 2
        # Main action buttons — bottom
        self._btn_new_game  = Button((cx - 130, 780, 260, 52),
                                     "NEW GAME", self.med_font)
        self._btn_lab       = Button((cx - 130, 846, 260, 52),
                                     "LABORATORY", self.med_font)

        # World select — previews + buttons in middle band
        n          = len(WORLDS)
        self._prev_w   = 170   # preview width
        self._prev_h   = 90    # preview height
        bw         = self._prev_w
        bh         = 38
        gap        = 10
        total_w    = n * bw + (n - 1) * gap
        start_x    = cx - total_w // 2
        self._prev_y   = 470   # preview top y
        self._btn_y    = self._prev_y + self._prev_h + 6  # button just below preview

        self._world_btns     = []
        self._world_previews = []
        for i, w in enumerate(WORLDS):
            bx = start_x + i * (bw + gap)
            self._world_btns.append(
                Button((bx, self._btn_y, bw, bh), w["name"], self.small_font,
                       border=(80, 60, 130))
            )
            self._world_previews.append(
                WorldPreview(i, self._prev_w, self._prev_h)
            )
        self._btn_dev       = Button((cfg.SCREEN_WIDTH - 114, cfg.SCREEN_HEIGHT - 36, 104, 28),
                                     "DEV MODE", self.tiny_font,
                                     color=(120, 100, 100),
                                     hover=(255, 180, 100),
                                     bg=(28, 20, 30),
                                     border=(80, 60, 60))
        self._btn_reset     = Button((10, cfg.SCREEN_HEIGHT - 36, 104, 28),
                                     "RESET ALL", self.tiny_font,
                                     color=(140, 80, 80),
                                     hover=(255, 100, 100),
                                     bg=(28, 16, 16),
                                     border=(100, 40, 40))

    def _build_lab_buttons(self):
        self._btn_lab_back   = Button((30, cfg.SCREEN_HEIGHT - 64, 160, 44),
                                      "BACK", self.font)
        cx = cfg.SCREEN_WIDTH // 2
        self._btn_tab_perm   = Button((cx - 200, 130, 180, 36),
                                      "Permanent", self.font)
        self._btn_tab_spell  = Button((cx + 20,  130, 180, 36),
                                      "Spells", self.font)
        self._hybrid_hovered = None
        self._hybrid_t       = 0.0
        self._spell_scroll   = 0    # pixel offset for left panel scroll

    def _build_dead_buttons(self):
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2
        self._btn_replay    = Button((cx - 200, cy + 100, 180, 48),
                                     "PLAY AGAIN", self.font)
        self._btn_main_menu = Button((cx + 20,  cy + 100, 180, 48),
                                     "MAIN MENU",  self.font)

    def _build_pause_buttons(self):
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2
        self._btn_resume    = Button((cx - 130, cy + 10,  260, 48),
                                     "RESUME", self.font)
        self._btn_quit_run  = Button((cx - 130, cy + 70,  260, 48),
                                     "QUIT TO MENU", self.font,
                                     border=(180, 80, 80))

    # ---------------------------------------------------------------- init run

    def new_run(self):
        self.run_data["total_runs"] += 1
        rd.save(self.run_data)

        self.level          = 1
        self.kills          = 0
        self.total_kills    = 0
        self.survived       = 0.0
        self.shards_earned  = 0
        self.boss           = None
        self.boss_pending   = False
        self.shop_open      = True
        self.lab_tab        = "permanent"
        self._world_data    = get_world(self.run_data.get("current_world", 0))
        self._bg            = Background(self._world_data["id"],
                                         cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)

        self._build_level()
        self._build_dead_buttons()
        self.state = PLAYING

    def _build_level(self):
        wdata = getattr(self, "_world_data",
                        get_world(self.run_data.get("current_world", 0)))
        diff  = difficulty_for_level(self.level) * wdata["diff_mult"]
        self.wizard       = Wizard(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)
        rd.apply_perms_to_wizard(self.wizard, self.run_data)
        rd.apply_spells_to_wizard(self.wizard, self.run_data)
        self.spell_engine = SpellEngine(self.wizard, self.run_data)
        self.spawner      = Spawner(difficulty=diff,
                                    world_enemies=wdata["enemies"])
        self.enemies      = []
        self.bolts        = []
        self.numbers      = []
        self.shake        = ScreenShake()
        self.kills        = 0
        self.kills_needed = kills_for_level(self.level)
        self.shop_open    = True

        if self.boss_pending:
            self._spawn_boss()
            self.boss_pending = False

    def _spawn_boss(self):
        self.boss = Boss(cfg.SCREEN_WIDTH // 2, -60, self.level)
        self.spawner.active = False
        self.state = BOSS_FIGHT

    # --------------------------------------------------------------- events

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            # F11 toggles fullscreen from any state
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self._toggle_fullscreen()
                continue

            # Remap mouse positions to canvas space for all click events
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                event = pygame.event.Event(event.type, {
                    **event.__dict__,
                    "pos": self._to_canvas(event.pos)
                })

            # --- Title ---
            if self.state == TITLE:
                if self._btn_new_game.clicked(event):
                    self.new_run()
                if self._btn_lab.clicked(event):
                    self.state = LABORATORY
                if self._btn_dev.clicked(event):
                    self.run_data["shards"] = 999999
                    self.run_data["highest_world"] = len(WORLDS) - 1
                    rd.save(self.run_data)
                if self._btn_reset.clicked(event):
                    rd.reset(self.run_data)
                    self._bg = Background(0, cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
                for i, btn in enumerate(self._world_btns):
                    if btn.clicked(event) and is_unlocked(i, self.run_data):
                        self.run_data["current_world"] = i
                        rd.save(self.run_data)
                        self._bg = Background(i, cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.quit()

            # --- Laboratory ---
            elif self.state == LABORATORY:
                if self._btn_lab_back.clicked(event):
                    self.state = TITLE
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = TITLE
                    self._handle_lab_key(event.key)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_lab_click(event.pos)
                if event.type == pygame.MOUSEWHEEL and self.lab_tab == "spells":
                    self._spell_scroll = max(0, self._spell_scroll - event.y * 30)

            # --- Dead ---
            elif self.state == DEAD:
                if self._btn_replay.clicked(event):
                    self.new_run()
                if self._btn_main_menu.clicked(event):
                    self.state = TITLE

            # --- Paused ---
            elif self.state == PAUSED:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = self._pre_pause_state
                if self._btn_resume.clicked(event):
                    self.state = self._pre_pause_state
                if self._btn_quit_run.clicked(event):
                    self.state = TITLE

            # --- Playing / Boss ---
            elif self.state in (PLAYING, BOSS_FIGHT):
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k == pygame.K_ESCAPE:
                        self._pre_pause_state = self.state
                        self._build_pause_buttons()
                        self.state = PAUSED
                    if k in (pygame.K_TAB, pygame.K_u):
                        self.shop_open = not self.shop_open
                    if self.shop_open:
                        picks = {
                            pygame.K_1: SHOP_KEYS[0],
                            pygame.K_2: SHOP_KEYS[1],
                            pygame.K_3: SHOP_KEYS[2],
                            pygame.K_4: SHOP_KEYS[3],
                        }
                        key = picks.get(k)
                        if key:
                            up.apply(key, self.wizard)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.shop_open:
                        self._handle_shop_click(event.pos)

    def _handle_lab_key(self, key):
        if key == pygame.K_TAB:
            self.lab_tab = "spells" if self.lab_tab == "permanent" else "permanent"
            self._spell_scroll = 0
            return
        picks = {pygame.K_1: 0, pygame.K_2: 1,
                 pygame.K_3: 2, pygame.K_4: 3}
        idx = picks.get(key)
        if idx is None:
            return
        if self.lab_tab == "permanent":
            keys = list(rd.PERM_COSTS.keys())
            if idx < len(keys):
                rd.buy_perm(keys[idx], self.run_data)
        else:
            # 1-4 buy the spell if not owned; no keyboard mod shortcuts
            keys = list(rd.SPELL_NAMES.keys())
            if idx < len(keys):
                rd.buy_spell(keys[idx], self.run_data)

    def _handle_lab_click(self, pos):
        # Tab switches
        if self._btn_tab_perm.clicked_pos(pos):
            self.lab_tab = "permanent"
            self._spell_scroll = 0
            return
        if self._btn_tab_spell.clicked_pos(pos):
            self.lab_tab = "spells"
            self._spell_scroll = 0
            return

        if self.lab_tab == "permanent":
            # Permanent upgrade rows
            for i in range(4):
                row = self._lab_row_rect(i)
                if row.collidepoint(pos):
                    keys = list(rd.PERM_COSTS.keys())
                    if i < len(keys):
                        rd.buy_perm(keys[i], self.run_data)
                    return

        elif self.lab_tab == "spells":
            # Right side: hybrid tree node clicks
            if hasattr(self, "_hybrid_hit_rects"):
                for spell_id, rect in self._hybrid_hit_rects.items():
                    if rect.collidepoint(pos):
                        if spell_id in rd.SPELL_NAMES:
                            rd.buy_spell(spell_id, self.run_data)
                        else:
                            ht.buy_hybrid(spell_id, self.run_data)
                        return

            # Left side: scrollable spell panel sub-card clicks
            panel_x   = 14
            panel_top = 175
            panel_bot = cfg.SCREEN_HEIGHT - 70
            left_w    = cfg.SCREEN_WIDTH // 2 - 20
            px, py    = pos

            if not (panel_x <= px <= panel_x + left_w and panel_top <= py <= panel_bot):
                return

            scroll      = getattr(self, "_spell_scroll", 0)
            owned_row_h = 162
            gap         = 8
            pad         = 8
            card_w      = (left_w - pad * 5) // 4
            card_h      = 80

            spell_keys    = list(rd.SPELL_NAMES.keys())
            owned_base    = [k for k in spell_keys if rd.spell_owned(k, self.run_data)]
            owned_hybrids = [h["id"] for h in ht.HYBRID_TREE
                             if ht.is_unlocked(h["id"], self.run_data)
                             and h["id"] in rd.SPELL_MODS]
            all_owned = owned_base + owned_hybrids

            # Content-space y position of the click
            content_y = (py - panel_top) + scroll
            content_x = px - panel_x

            cur_y = 0
            for key in all_owned:
                row_top = cur_y
                row_bot = cur_y + owned_row_h
                if row_top <= content_y <= row_bot:
                    # Check each sub-card
                    mod_keys = list(rd.SPELL_MODS.get(key, {}).keys())
                    for j, mod_key in enumerate(mod_keys):
                        sub_x = pad + j * (card_w + pad)
                        sub_y = owned_row_h - card_h - pad
                        sub   = pygame.Rect(sub_x, sub_y, card_w, card_h)
                        if (sub_x <= content_x <= sub_x + card_w and
                                cur_y + sub_y <= content_y <= cur_y + sub_y + card_h):
                            rd.buy_spell_mod(key, mod_key, self.run_data)
                            return
                cur_y += owned_row_h + gap

    def _handle_shop_click(self, pos):
        for i, key in enumerate(SHOP_KEYS):
            card = self._shop_card_rect(i)
            if card.collidepoint(pos):
                up.apply(key, self.wizard)

    # --------------------------------------------------------------- update

    def update(self, dt):
        if hasattr(self, "_bg"):
            self._bg.update(dt)
        if self.state == LABORATORY:
            self._hybrid_t = getattr(self, "_hybrid_t", 0.0) + dt
            if self.lab_tab == "spells" and hasattr(self, "_hybrid_hit_rects"):
                mx, my = self._to_canvas(pygame.mouse.get_pos())
                self._hybrid_hovered = None
                for sid, rect in self._hybrid_hit_rects.items():
                    if rect.collidepoint(mx, my):
                        # Only highlight if owned or available to unlock
                        if ht.is_unlocked(sid, self.run_data) or \
                           ht.can_unlock(sid, self.run_data) or \
                           (sid in rd.SPELL_NAMES):  # base spells always hoverable
                            self._hybrid_hovered = sid
                        break
        if self.state == TITLE:
            self._title_spin = (self._title_spin + dt * 0.8) % (math.pi * 2)
            if hasattr(self, "_world_previews"):
                for p in self._world_previews:
                    p.update(dt)
            self._update_title_enemies(dt)
            return
        if self.state not in (PLAYING, BOSS_FIGHT):
            return

        self.survived += dt
        self.shake.update(dt)
        self.spawner.update(dt, self.enemies)

        all_targets = self.enemies + ([self.boss] if self.boss else [])
        self.wizard.update(dt, all_targets, self.bolts)

        for entity in all_targets:
            dealt = entity.update(dt, self.wizard)
            if dealt:
                self.shake.add(2.5)
                self.numbers.append(
                    DamageNumber(self.wizard.pos, dealt, (255, 120, 120)))

        for bolt in self.bolts:
            bolt.update(dt)
            for entity, amount in bolt.check_hit(all_targets):
                self.numbers.append(DamageNumber(entity.pos, amount))
                self.spell_engine.on_bolt_hit(entity, amount)

        self.spell_engine.update(dt, self.enemies)

        self.resolve_deaths()

        for n in self.numbers:
            n.update(dt)

        self.bolts   = [b for b in self.bolts if not b.done]
        self.numbers = [n for n in self.numbers if not n.done]

        if not self.wizard.alive:
            self._on_death()

    def resolve_deaths(self):
        survivors, spawned = [], []
        for enemy in self.enemies:
            if enemy.alive:
                survivors.append(enemy)
                continue
            self.kills += 1
            self.total_kills += 1
            self.wizard.mana += enemy.mana
            spawned.extend(enemy.spawn_on_death())
            self.spell_engine.on_kill(enemy, self.enemies)
        self.enemies = survivors + spawned

        if self.boss and not self.boss.alive:
            shards = self.boss.shards
            self.shards_earned += shards
            self.run_data["shards"] += shards
            rd.save(self.run_data)
            self.numbers.append(
                DamageNumber(self.boss.pos, shards, cfg.COLOR_SHARD))
            self.boss = None
            self.spawner.active = True
            self.state = PLAYING

        if self.state == PLAYING and self.kills >= self.kills_needed:
            self._advance_level()

    def _advance_level(self):
        self.level += 1
        self.kills        = 0
        self.kills_needed = kills_for_level(self.level)

        wdata = getattr(self, "_world_data",
                        get_world(self.run_data.get("current_world", 0)))
        diff = difficulty_for_level(self.level) * wdata["diff_mult"]
        self.spawner.difficulty      = diff
        self.spawner._interval_start = max(
            cfg.SPAWN_INTERVAL_MIN + 0.05,
            cfg.SPAWN_INTERVAL_START * (1.0 / diff))

        self._check_world_advance()

        is_boss_level = (self.level % cfg.BOSS_EVERY == 0)
        if is_boss_level:
            self.boss_pending = True
            self._spawn_boss()
            self.boss_pending = False

    def _reapply_run_upgrades(self):
        for key, level in self.wizard.upgrade_levels.items():
            data = up.SHOP_UPGRADES[key]
            stat = data["stat"]
            for _ in range(level):
                if "factor" in data:
                    val = getattr(self.wizard, stat) * data["factor"]
                    if "floor" in data:
                        val = max(data["floor"], val)
                    setattr(self.wizard, stat, val)
                else:
                    setattr(self.wizard, stat,
                            getattr(self.wizard, stat) + data["amount"])

    def _on_death(self):
        if self.level > self.run_data["best_level"]:
            self.run_data["best_level"] = self.level
        shards = rd.shards_for_level(self.level)
        self.shards_earned += shards
        self.run_data["shards"] += shards
        rd.save(self.run_data)
        self.state = DEAD

    def _check_world_advance(self):
        """Call when a new level is reached — unlock next world at level 100."""
        if self.level < 100:
            return
        cur = self.run_data.get("current_world", 0)
        next_world = cur + 1
        if next_world < len(WORLDS):
            self.run_data["highest_world"] = max(
                self.run_data.get("highest_world", 0), next_world)
            self.run_data["current_world"] = next_world
            self._world_data = get_world(next_world)
            self._bg = Background(next_world, cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
            # Update spawner to new world enemies
            wdata = self._world_data
            diff  = difficulty_for_level(self.level) * wdata["diff_mult"]
            self.spawner.difficulty     = diff
            self.spawner._world_enemies = wdata["enemies"]
            rd.save(self.run_data)

    # --------------------------------------------------------------- draw

    def draw(self):
        # All drawing goes to the fixed canvas
        self.canvas.fill((0, 0, 0))   # cleared; bg drawn per-state below
        real_screen = self.screen
        self.screen = self.canvas

        # Background drawn behind every screen
        if hasattr(self, "_bg"):
            self._bg.draw(self.screen)

        if self.state == TITLE:
            self.draw_title()
        elif self.state == LABORATORY:
            self.draw_laboratory()
        elif self.state == DEAD:
            self.draw_dead()
        elif self.state in (PLAYING, BOSS_FIGHT):
            self.draw_game()
        elif self.state == PAUSED:
            self.draw_game()
            self.draw_pause()

        self.screen = real_screen

        # Scale canvas to fill display, preserving aspect ratio with black bars
        dw, dh = self.screen.get_size()
        cw, ch = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        scale   = min(dw / cw, dh / ch)
        sw, sh  = int(cw * scale), int(ch * scale)
        ox, oy  = (dw - sw) // 2, (dh - sh) // 2

        self.screen.fill((0, 0, 0))
        scaled = pygame.transform.scale(self.canvas, (sw, sh))
        self.screen.blit(scaled, (ox, oy))

        # Store offset so mouse clicks and Button hover map to canvas coords
        self._display_offset = (ox, oy)
        self._display_scale  = scale
        Button._canvas_offset = (ox, oy)
        Button._canvas_scale  = scale

        pygame.display.flip()

    def draw_pause(self):
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2

        self.dim_screen(160)

        box = pygame.Rect(cx - 160, cy - 60, 320, 170)
        pygame.draw.rect(self.screen, cfg.COLOR_SHOP_BG, box, border_radius=10)
        pygame.draw.rect(self.screen, cfg.COLOR_SHOP_EDGE, box, 2, border_radius=10)

        title = self.med_font.render("PAUSED", True, cfg.COLOR_TEXT)
        self.screen.blit(title, title.get_rect(center=(cx, cy - 30)))

        sub = self.small_font.render("quit this run?", True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(center=(cx, cy + 2)))

        self._btn_resume.draw(self.screen)
        self._btn_quit_run.draw(self.screen)

    # ---------------------------------------------------------------- title

    def draw_title(self):
        W, H = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        cx   = W // 2

        # Rune rings (bg already drawn)
        for r in (100, 200, 300, 400):
            glow_circle(self.screen, (70, 50, 120), (cx, H // 2), r,
                        layers=1, max_alpha=20)
            pygame.draw.circle(self.screen, cfg.COLOR_RUNE, (cx, H // 2), r, 1)

        # Moon glow
        moon_x, moon_y = W - 100, 80
        glow_circle(self.screen, (200, 190, 140), (moon_x, moon_y),
                    60, layers=5, max_alpha=50)

        # Tower scene — left side, compact
        self._draw_title_scene(cx, H)

        # ---- Title band (top) ----
        for off, alpha in ((3, 40), (1, 80), (0, 255)):
            t = self.big_font.render("WIZARD SIEGE", True,
                                     (130, 80, 210) if off else (200, 160, 255))
            if off:
                s = pygame.Surface(t.get_size(), pygame.SRCALPHA)
                s.blit(t, (0, 0)); s.set_alpha(alpha)
                self.screen.blit(s, t.get_rect(center=(cx + off, 80 + off)))
            else:
                self.screen.blit(t, t.get_rect(center=(cx, 80)))

        sub = self.font.render("defend the tower. grow in power.",
                               True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(center=(cx, 136)))

        best = self.tiny_font.render(
            f"best level {self.run_data['best_level']}   "
            f"runs {self.run_data['total_runs']}",
            True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(best, best.get_rect(center=(cx, 162)))

        # Shard box — top right
        shards_surf = self.font.render(
            f"{self.run_data['shards']} Soul Shards", True, cfg.COLOR_SHARD)
        box_w  = shards_surf.get_width() + 44
        shard_x = W - box_w - 10
        pygame.draw.rect(self.screen, (28, 20, 44),
                         (shard_x, 10, box_w, 36), border_radius=6)
        pygame.draw.rect(self.screen, cfg.COLOR_SHARD,
                         (shard_x, 10, box_w, 36), 1, border_radius=6)
        self._draw_shard_crystal(self.screen, shard_x + 14, 28, 10)
        self.screen.blit(shards_surf, (shard_x + 28, 18))

        # ---- World select panel ----
        n   = len(WORLDS)
        bw  = self._prev_w
        gap = 10
        total_w = n * bw + (n-1) * gap
        panel_x = cx - total_w // 2 - 14
        panel_y = self._prev_y - 28
        panel_h = self._prev_h + 38 + 6 + 22   # preview + button + subtitle
        panel   = pygame.Rect(panel_x, panel_y, total_w + 28, panel_h)
        draw_rect_alpha(self.screen, (18, 15, 32), panel, 210, radius=10)
        pygame.draw.rect(self.screen, (55, 44, 90), panel, 1, border_radius=10)

        lbl = self.small_font.render("SELECT WORLD", True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(lbl, lbl.get_rect(centerx=cx, y=panel_y + 6))

        mx, my = pygame.mouse.get_pos()
        cur_world = self.run_data.get("current_world", 0)

        for i, (btn, wdata, preview) in enumerate(
                zip(self._world_btns, WORLDS, self._world_previews)):
            unlocked = is_unlocked(i, self.run_data)
            selected = (i == cur_world)
            hovered  = btn.rect.collidepoint(mx, my) or \
                       pygame.Rect(btn.rect.x, self._prev_y,
                                   self._prev_w, self._prev_h).collidepoint(mx, my)

            # Draw animated preview
            preview.draw(self.screen, btn.rect.x, self._prev_y,
                         unlocked, hovered)

            # Button styling
            btn.border = (180, 140, 255) if selected else \
                         (90, 70, 150)   if (unlocked and hovered) else \
                         (70, 55, 110)   if unlocked else (38, 34, 55)
            btn.color  = cfg.COLOR_TEXT  if unlocked else (60, 54, 78)
            btn.draw(self.screen)

            # Subtitle row below button
            if unlocked and selected:
                sub2 = self.tiny_font.render(wdata["name"], True, (180, 140, 255))
                self.screen.blit(sub2, sub2.get_rect(
                    centerx=btn.rect.centerx, y=btn.rect.bottom + 4))
            elif not unlocked:
                prev_name = WORLDS[i-1]["name"] if i > 0 else ""
                req = self.tiny_font.render(
                    f"Beat lv 100 — {prev_name}", True, (55, 48, 72))
                self.screen.blit(req, req.get_rect(
                    centerx=btn.rect.centerx, y=btn.rect.bottom + 4))

        # ---- Main buttons (bottom) ----
        self._btn_new_game.draw(self.screen)
        self._btn_lab.draw(self.screen)
        self._btn_dev.draw(self.screen)
        self._btn_reset.draw(self.screen)

    def _draw_title_scene(self, cx, H):
        # Stars scattered across upper portion only
        random.seed(42)
        for _ in range(60):
            sx = random.randint(0, cfg.SCREEN_WIDTH)
            sy = random.randint(0, 500)
            br = random.randint(80, 200)
            pygame.draw.circle(self.screen, (br, br, br + 30), (sx, sy), 1)
        random.seed()

        # Moon — top right
        mx, my = cfg.SCREEN_WIDTH - 100, 80
        pygame.draw.circle(self.screen, (220, 210, 180), (mx, my), 36)
        pygame.draw.circle(self.screen, (14, 12, 22), (mx + 12, my - 8), 28)

        # Tower — centered, sits in the 200-530 band (above world select panel)
        tx, ty = cx - 22, 220
        tw, th = 44, 130
        pygame.draw.rect(self.screen, (45, 38, 70), (tx, ty, tw, th))
        pygame.draw.rect(self.screen, (70, 60, 100), (tx, ty, tw, th), 2)

        # Battlements
        for bx in range(tx, tx + tw, 10):
            pygame.draw.rect(self.screen, (55, 46, 80), (bx, ty - 10, 7, 10))

        # Tower windows
        for wy in (ty + 22, ty + 55, ty + 88):
            pygame.draw.ellipse(self.screen, (255, 220, 100),
                                (cx - 5, wy, 10, 13))
            pygame.draw.ellipse(self.screen, (255, 255, 180),
                                (cx - 2, wy + 3, 4, 7))

        # Subtle ground shadow — just under the tower, fades out sideways
        ground_y = ty + th
        shadow_w = 300
        shadow = pygame.Surface((shadow_w, 8), pygame.SRCALPHA)
        for sx in range(shadow_w):
            t_fade = 1 - abs(sx - shadow_w // 2) / (shadow_w // 2)
            alpha = int(80 * t_fade)
            pygame.draw.line(shadow, (50, 44, 72, alpha),
                             (sx, 0), (sx, 7))
        self.screen.blit(shadow, (cx - shadow_w // 2, ground_y))

        # Orbiting motes around tower tip
        for i in range(3):
            angle = self._title_spin + i * math.pi * 2 / 3
            mx2 = cx + math.cos(angle) * 32
            my2 = (ty - 8) + math.sin(angle) * 13
            glow_circle(self.screen, cfg.COLOR_BOLT, (int(mx2), int(my2)),
                        5, layers=2, max_alpha=100)
            pygame.draw.circle(self.screen, cfg.COLOR_BOLT,
                               (int(mx2), int(my2)), 4)

        # Animated enemy march
        for e in getattr(self, "_title_enemies", []):
            e.draw(self.screen)
        for b in getattr(self, "_title_bolts", []):
            b.draw(self.screen)

    def _draw_shard_crystal(self, surface, x, y, r):
        pts = [
            (x, y - r),
            (x + r * 0.6, y - r * 0.2),
            (x + r * 0.4, y + r),
            (x - r * 0.4, y + r),
            (x - r * 0.6, y - r * 0.2),
        ]
        pygame.draw.polygon(surface, cfg.COLOR_SHARD, pts)
        pygame.draw.polygon(surface, (255, 230, 255), pts, 1)

    # ------------------------------------------------------------ laboratory

    def _lab_row_rect(self, i, owned=False):
        """Return row rect. Owned spell rows are taller to fit sub-cards."""
        panel_x = cfg.SCREEN_WIDTH // 2 - 310
        panel_w = 620
        row_h_normal = 68
        row_h_owned  = 158
        spell_keys = list(rd.SPELL_NAMES.keys())
        y = 185
        for idx in range(i):
            key = spell_keys[idx] if self.lab_tab == "spells" else None
            is_owned = key and rd.spell_owned(key, self.run_data)
            y += (row_h_owned if is_owned else row_h_normal) + 8
        h = row_h_owned if owned else row_h_normal
        return pygame.Rect(panel_x, y, panel_w, h)

    def _spell_sub_card_rect(self, row, j):
        """Rect for the jth mod sub-card inside an owned spell row."""
        pad    = 8
        n      = 4
        card_w = (row.width - pad * (n + 1)) // n
        card_h = 78
        x = row.x + pad + j * (card_w + pad)
        y = row.y + row.height - card_h - pad
        return pygame.Rect(x, y, card_w, card_h)

    def draw_laboratory(self):
        W, H = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        cx = W // 2

        for r in (120, 240, 360):
            pygame.draw.circle(self.screen, cfg.COLOR_RUNE, (cx, H // 2), r, 1)

        # Title — crystals placed well clear of text
        title = self.big_font.render("LABORATORY", True, cfg.COLOR_SHARD)
        title_rect = title.get_rect(center=(cx, 60))
        self.screen.blit(title, title_rect)
        margin = 24
        self._draw_shard_crystal(self.screen,
                                 title_rect.left - margin, 60, 12)
        self._draw_shard_crystal(self.screen,
                                 title_rect.right + margin, 60, 12)

        # Shard count
        shards_surf = self.med_font.render(
            f"{self.run_data['shards']}  Soul Shards", True, cfg.COLOR_SHARD)
        self.screen.blit(shards_surf, shards_surf.get_rect(center=(cx, 100)))

        # Tab buttons — highlight active
        active_border = (200, 160, 255)
        inactive_border = (70, 60, 120)
        for btn, tab in ((self._btn_tab_perm, "permanent"),
                         (self._btn_tab_spell, "spells")):
            btn.border = active_border if self.lab_tab == tab else inactive_border
            btn.draw(self.screen)

        # Tab hint
        hint = self.tiny_font.render("TAB to switch tabs",
                                     True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(centerx=cx, y=H - 80))

        # Rows
        if self.lab_tab == "permanent":
            keys      = list(rd.PERM_COSTS.keys())
            names     = rd.PERM_NAMES
            descs     = rd.PERM_DESCS
            cost_fn   = rd.perm_cost
            maxed_fn  = rd.perm_maxed
            afford_fn = rd.can_afford_perm
            level_key = "perm_levels"
            self._draw_lab_perm_rows(keys, names, descs, cost_fn, maxed_fn, afford_fn, level_key)
        else:
            self._draw_lab_spell_list()

        self._btn_lab_back.draw(self.screen)

    def _draw_lab_perm_rows(self, keys, names, descs, cost_fn, maxed_fn, afford_fn, level_key):
        for i, key in enumerate(keys):
            row        = self._lab_row_rect(i)
            maxed      = maxed_fn(key, self.run_data)
            affordable = afford_fn(key, self.run_data)
            c          = cost_fn(key, self.run_data)
            level      = self.run_data[level_key][key]
            bg = cfg.COLOR_SHOP_HOVER if affordable and not maxed else cfg.COLOR_CARD
            pygame.draw.rect(self.screen, bg, row, border_radius=8)
            pygame.draw.rect(self.screen, cfg.COLOR_SHARD, row, 1, border_radius=8)
            self.screen.blit(self.font.render(f"[{i+1}]", True, cfg.COLOR_TEXT_DIM),
                             (row.x + 12, row.y + 8))
            self.screen.blit(self.med_font.render(names[key], True, cfg.COLOR_TEXT),
                             (row.x + 52, row.y + 6))
            self.screen.blit(self.small_font.render(descs[key], True, cfg.COLOR_TEXT_DIM),
                             (row.x + 52, row.y + 40))
            counter = self.font.render(f"{level}/100", True, cfg.COLOR_SHARD)
            self.screen.blit(counter, (row.right - 160, row.y + 8))
            if maxed:
                st = self.font.render("MAXED", True, cfg.COLOR_TEXT_DIM)
            else:
                col = cfg.COLOR_SHARD if affordable else (160, 80, 80)
                st  = self.font.render(f"{c} shards", True, col)
            self.screen.blit(st, (row.right - 160, row.y + 38))

    def _draw_lab_spell_list(self):
        W, H = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT

        # ---- Left half: scrollable spell panel ----
        panel_x    = 14
        panel_top  = 175
        panel_bot  = H - 70
        panel_h    = panel_bot - panel_top
        left_w     = W // 2 - 20
        owned_row_h = 162
        unowned_h   = 48
        gap         = 8

        spell_keys   = list(rd.SPELL_NAMES.keys())
        owned_spells = [k for k in spell_keys if rd.spell_owned(k, self.run_data)]
        # Add owned hybrid spells that have mods defined
        owned_hybrids = [h["id"] for h in ht.HYBRID_TREE
                         if ht.is_unlocked(h["id"], self.run_data)
                         and h["id"] in rd.SPELL_MODS]
        owned_spells += owned_hybrids
        unowned      = [k for k in spell_keys if not rd.spell_owned(k, self.run_data)]

        # Compute total content height for scroll capping
        total_h = max(100, len(owned_spells) * (owned_row_h + gap))
        self._spell_scroll = max(0, min(self._spell_scroll,
                                        max(0, total_h - panel_h)))

        # Draw into an off-screen surface then blit with clip
        content = pygame.Surface((left_w, max(total_h + 20, panel_h)), pygame.SRCALPHA)
        cur_y = 0

        # Owned spells — expanded with mod sub-cards
        for key in owned_spells:
            # Name and desc — check base spells first, then hybrids
            if key in rd.SPELL_NAMES:
                spell_name = rd.SPELL_NAMES[key]
                spell_desc = rd.SPELL_DESCS[key]
            else:
                hentry     = ht.HYBRID_BY_ID.get(key, {})
                spell_name = hentry.get("name", key.replace("_"," ").title())
                spell_desc = hentry.get("desc", "")
            row = pygame.Rect(0, cur_y, left_w, owned_row_h)
            pygame.draw.rect(content, (22, 40, 22), row, border_radius=8)
            pygame.draw.rect(content, (80, 200, 80), row, 1, border_radius=8)
            content.blit(self.med_font.render(spell_name, True, cfg.COLOR_TEXT),
                         (12, cur_y + 8))
            content.blit(self.small_font.render(spell_desc, True, cfg.COLOR_TEXT_DIM),
                         (12, cur_y + 34))

            mod_keys = list(rd.SPELL_MODS[key].keys())
            pad    = 8
            card_w = (left_w - pad * 5) // 4
            card_h = 80
            for j, mod_key in enumerate(mod_keys):
                sx  = pad + j * (card_w + pad)
                sy  = cur_y + owned_row_h - card_h - pad
                sub = pygame.Rect(sx, sy, card_w, card_h)
                mod_data       = rd.SPELL_MODS[key][mod_key]
                level          = self.run_data["spell_mods"][key][mod_key]
                maxed          = rd.spell_mod_maxed(key, mod_key, self.run_data)
                affordable_mod = rd.can_afford_spell_mod(key, mod_key, self.run_data)
                mc             = rd.spell_mod_cost(key, mod_key, self.run_data)

                sub_bg = (35, 65, 35) if affordable_mod and not maxed else (18, 32, 18)
                bc     = (80, 170, 80) if affordable_mod else (40, 80, 40)
                pygame.draw.rect(content, sub_bg, sub, border_radius=5)
                pygame.draw.rect(content, bc, sub, 1, border_radius=5)

                def blit_c(surf, x, y, sub=sub):
                    clip_w = sub.right - x - 4
                    if clip_w > 0:
                        content.blit(surf, (x, y),
                                     pygame.Rect(0, 0, clip_w, surf.get_height()))

                blit_c(self.small_font.render(mod_data["name"], True, cfg.COLOR_TEXT),
                       sub.x+6, sub.y+5)
                blit_c(self.tiny_font.render(f"{level}/100", True, (120,210,120)),
                       sub.x+6, sub.y+27)
                if maxed:
                    cs = self.tiny_font.render("MAXED", True, cfg.COLOR_TEXT_DIM)
                else:
                    col = (120,230,140) if affordable_mod else (160,80,80)
                    cs  = self.tiny_font.render(f"{mc}s", True, col)
                blit_c(cs, sub.x+6, sub.y+44)
                blit_c(self.tiny_font.render(mod_data["desc"], True, cfg.COLOR_TEXT_DIM),
                       sub.x+6, sub.y+sub.height-16)

            cur_y += owned_row_h + gap

        # If nothing owned yet, show hint
        if not owned_spells:
            hint = self.small_font.render(
                "Click spells on the tree to unlock →", True, cfg.COLOR_TEXT_DIM)
            content.blit(hint, hint.get_rect(center=(left_w//2, 40)))

        # Blit clipped region to screen
        clip_rect = pygame.Rect(0, self._spell_scroll, left_w, panel_h)
        self.screen.blit(content, (panel_x, panel_top), clip_rect)

        # Scroll indicator
        if total_h > panel_h:
            track_h = panel_h
            thumb_h = max(30, int(panel_h * panel_h / total_h))
            thumb_y = int(panel_top + (self._spell_scroll / (total_h - panel_h))
                          * (track_h - thumb_h))
            pygame.draw.rect(self.screen, (50, 44, 70),
                             (panel_x + left_w + 2, panel_top, 4, track_h),
                             border_radius=2)
            pygame.draw.rect(self.screen, (120, 100, 180),
                             (panel_x + left_w + 2, thumb_y, 4, thumb_h),
                             border_radius=2)

        # ---- Right half: hybrid tree ----
        tree_cx = W * 3 // 4
        tree_cy = H // 2 + 20

        # Divider line
        pygame.draw.line(self.screen, (50, 44, 80),
                         (W // 2, 170), (W // 2, H - 80), 1)

        tree_label = self.small_font.render("HYBRID TREE", True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(tree_label, tree_label.get_rect(centerx=tree_cx, y=175))

        self._hybrid_hit_rects = ht.draw_tree(
            self.screen, tree_cx, tree_cy, self.run_data,
            getattr(self, "_hybrid_hovered", None),
            self.small_font, self.tiny_font,
            getattr(self, "_hybrid_t", 0.0))

        # Tooltip for hovered node (base spell or hybrid)
        hov = getattr(self, "_hybrid_hovered", None)
        if hov and hov in rd.SPELL_NAMES and not rd.spell_owned(hov, self.run_data):
            # Base spell not yet owned — show purchase info
            c      = rd.spell_cost(hov, self.run_data)
            afford = rd.can_afford_spell(hov, self.run_data)
            tw, th = 300, 70
            tx = cfg.SCREEN_WIDTH // 2 + 10
            ty = cfg.SCREEN_HEIGHT - th - 80
            draw_rect_alpha(self.screen, (24, 20, 40),
                            pygame.Rect(tx, ty, tw, th), 220, radius=8)
            pygame.draw.rect(self.screen, cfg.COLOR_SHARD,
                             (tx, ty, tw, th), 1, border_radius=8)
            self.screen.blit(
                self.font.render(rd.SPELL_NAMES[hov], True, cfg.COLOR_TEXT),
                (tx + 10, ty + 8))
            self.screen.blit(
                self.small_font.render(rd.SPELL_DESCS[hov], True, cfg.COLOR_TEXT_DIM),
                (tx + 10, ty + 30))
            col = cfg.COLOR_SHARD if afford else (160, 80, 80)
            self.screen.blit(
                self.small_font.render(f"{c} shards — click to buy", True, col),
                (tx + 10, ty + 50))
        elif (hov and hov in ht.HYBRID_BY_ID and
              (ht.is_unlocked(hov, self.run_data) or
               ht.can_unlock(hov, self.run_data))):
            entry  = ht.HYBRID_BY_ID[hov]
            owned  = ht.is_unlocked(hov, self.run_data)
            avail  = ht.can_unlock(hov, self.run_data)
            afford = ht.can_afford(hov, self.run_data)
            if owned:
                cost_str = "OWNED"
                col = (80, 200, 80)
            elif avail:
                cost_str = f"{entry['cost']} shards"
                col = cfg.COLOR_SHARD if afford else (160, 80, 80)
            else:
                reqs = ", ".join(r.replace("_", " ").title()
                                 for r in entry["requires"])
                cost_str = f"Needs: {reqs}"
                col = cfg.COLOR_TEXT_DIM

            tw, th = 320, 70
            tx = W // 2 + 10
            ty = H - th - 80
            draw_rect_alpha(self.screen, (24, 20, 40),
                            pygame.Rect(tx, ty, tw, th), 220, radius=8)
            pygame.draw.rect(self.screen, cfg.COLOR_SHARD,
                             (tx, ty, tw, th), 1, border_radius=8)
            self.screen.blit(
                self.font.render(entry["name"], True, cfg.COLOR_TEXT),
                (tx + 10, ty + 8))
            self.screen.blit(
                self.small_font.render(entry["desc"], True, cfg.COLOR_TEXT_DIM),
                (tx + 10, ty + 30))
            self.screen.blit(
                self.small_font.render(cost_str, True, col),
                (tx + 10, ty + 50))

    # -------------------------------------------------------------- dead screen

    def draw_dead(self):
        cx = cfg.SCREEN_WIDTH // 2
        cy = cfg.SCREEN_HEIGHT // 2

        for r in (120, 240, 360):
            pygame.draw.circle(self.screen, cfg.COLOR_RUNE, (cx, cy), r, 1)

        title = self.big_font.render("THE WIZARD FALLS", True, cfg.COLOR_TEXT)
        self.screen.blit(title, title.get_rect(center=(cx, cy - 140)))

        stats = [
            f"Reached Level {self.level}",
            f"{self.total_kills} enemies slain",
            f"Shards earned:  +{self.shards_earned}",
        ]
        for i, line in enumerate(stats):
            s = self.font.render(line, True, cfg.COLOR_TEXT_DIM)
            self.screen.blit(s, s.get_rect(center=(cx, cy - 70 + i * 28)))

        # Shard total
        total = self.med_font.render(
            f"Total Shards: {self.run_data['shards']}", True, cfg.COLOR_SHARD)
        self.screen.blit(total, total.get_rect(center=(cx, cy + 60)))

        self._btn_replay.draw(self.screen)
        self._btn_main_menu.draw(self.screen)

    # -------------------------------------------------------------- gameplay

    def draw_game(self):
        offset = self.shake.offset

        # Draw world background
        self._bg.draw(self.screen)
        self.draw_runes(offset)
        self.spell_engine.draw(self.screen, offset)
        for bolt in self.bolts:
            bolt.draw(self.screen, offset)
        self.wizard.draw(self.screen, offset)
        for enemy in self.enemies:
            enemy.draw(self.screen, offset)
        if self.boss:
            self.boss.draw(self.screen, offset)
        for n in self.numbers:
            n.draw(self.screen, self.small_font, offset)

        self.draw_hud()
        if self.shop_open:
            self.draw_shop()

    def draw_runes(self, offset):
        center = self.wizard.pos + offset
        for r in (120, 240, 360):
            pygame.draw.circle(self.screen, cfg.COLOR_RUNE, center, r, 1)

    def draw_hud(self):
        x, y = 16, 16
        bar_w, bar_h = 250, 16

        pct = self.wizard.hp / self.wizard.max_hp
        pygame.draw.rect(self.screen, cfg.COLOR_HP_BG, (x, y, bar_w, bar_h))
        pygame.draw.rect(self.screen, cfg.COLOR_WIZARD_HP,
                         (x, y, bar_w * pct, bar_h))
        # Glow on HP bar
        glow_rect(self.screen, cfg.COLOR_WIZARD_HP,
                  pygame.Rect(x, y, int(bar_w * pct), bar_h),
                  radius=2, layers=2, max_alpha=50)
        pygame.draw.rect(self.screen, cfg.COLOR_TEXT_DIM,
                         (x, y, bar_w, bar_h), 1)
        self.blit(f"{int(self.wizard.hp)} / {int(self.wizard.max_hp)}",
                  x + bar_w + 10, y - 2)

        # Level progress bar — purple
        ly = y + bar_h + 6
        lpct = min(1.0, self.kills / self.kills_needed)
        pygame.draw.rect(self.screen, (28, 20, 44), (x, ly, bar_w, 10))
        pygame.draw.rect(self.screen, cfg.COLOR_LEVEL_BAR,
                         (x, ly, bar_w * lpct, 10))
        pygame.draw.rect(self.screen, cfg.COLOR_TEXT_DIM, (x, ly, bar_w, 10), 1)
        self.blit(f"Lv {self.level}  {self.kills}/{self.kills_needed}",
                  x + bar_w + 10, ly - 3, dim=True)

        my = ly + 18
        self.screen.blit(
            self.font.render(f"Mana  {self.wizard.mana}", True, cfg.COLOR_MANA),
            (x, my))
        self.screen.blit(
            self.font.render(f"Shards {self.run_data['shards']}",
                             True, cfg.COLOR_SHARD),
            (x, my + 22))

        wname = getattr(self, "_world_data", get_world(0))["name"]
        lines = [f"World  {wname}", f"Slain  {self.total_kills}"]
        for i, line in enumerate(lines):
            self.blit(line, x, my + 50 + i * 20, dim=True)

        if self.state == BOSS_FIGHT:
            warn = self.med_font.render("BOSS", True, (220, 60, 255))
            self.screen.blit(warn, warn.get_rect(
                centerx=cfg.SCREEN_WIDTH // 2, y=16))

        hint = self.tiny_font.render("ESC menu", True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(hint, (x, my + 50 + len(lines) * 20 + 6))

    # ---------------------------------------------------------------- shop helpers

    def _shop_card_rect(self, i):
        panel_h = 110
        card_w  = (cfg.SCREEN_WIDTH - 28) // 4 - 6
        card_h  = 62
        card_y  = cfg.SCREEN_HEIGHT - panel_h + 34
        cx      = 14 + i * (card_w + 6)
        return pygame.Rect(cx, card_y, card_w, card_h)

    def draw_shop(self):
        panel_h = 110
        panel_y = cfg.SCREEN_HEIGHT - panel_h
        pygame.draw.rect(self.screen, cfg.COLOR_SHOP_BG,
                         (0, panel_y, cfg.SCREEN_WIDTH, panel_h))
        # Glowing top border
        glow_rect(self.screen, cfg.COLOR_SHOP_EDGE,
                  pygame.Rect(0, panel_y, cfg.SCREEN_WIDTH, panel_h),
                  radius=0, layers=2, max_alpha=50)
        pygame.draw.line(self.screen, cfg.COLOR_SHOP_EDGE,
                         (0, panel_y), (cfg.SCREEN_WIDTH, panel_y), 2)

        hx, hy = 14, panel_y + 8
        self.screen.blit(self.font.render("ARCANE SHOP", True, cfg.COLOR_TEXT), (hx, hy))
        self.screen.blit(
            self.font.render(f"Mana: {self.wizard.mana}", True, cfg.COLOR_MANA),
            (hx + 180, hy))
        hint = self.small_font.render("click or press 1-4  •  TAB to toggle",
                                      True, cfg.COLOR_TEXT_DIM)
        self.screen.blit(hint, (cfg.SCREEN_WIDTH - hint.get_width() - 14, hy + 4))

        for i, key in enumerate(SHOP_KEYS):
            data       = up.SHOP_UPGRADES[key]
            card       = self._shop_card_rect(i)
            maxed      = up.is_maxed(key, self.wizard)
            affordable = up.can_afford(key, self.wizard)
            c          = up.cost(key, self.wizard)
            level      = self.wizard.upgrade_levels[key]

            bg = cfg.COLOR_SHOP_HOVER if affordable and not maxed else cfg.COLOR_CARD
            pygame.draw.rect(self.screen, bg, card, border_radius=6)
            pygame.draw.rect(self.screen, cfg.COLOR_SHOP_EDGE, card, 1, border_radius=6)

            # Row 1: key hint + name
            self.screen.blit(
                self.small_font.render(f"[{i+1}]", True, cfg.COLOR_TEXT_DIM),
                (card.x + 6, card.y + 6))
            self.screen.blit(
                self.font.render(data["name"], True, cfg.COLOR_TEXT),
                (card.x + 36, card.y + 4))

            # Row 2: counter left, cost right
            self.screen.blit(
                self.small_font.render(f"{level}/100", True, cfg.COLOR_MANA),
                (card.x + 6, card.y + 28))
            if maxed:
                st = self.small_font.render("MAXED", True, cfg.COLOR_TEXT_DIM)
            else:
                col = cfg.COLOR_MANA if affordable else (160, 80, 80)
                st  = self.small_font.render(f"{c} mana", True, col)
            self.screen.blit(st, (card.right - st.get_width() - 6, card.y + 28))

            # Row 3: desc
            self.screen.blit(
                self.small_font.render(data["desc"], True, cfg.COLOR_TEXT_DIM),
                (card.x + 6, card.y + 46))

    # ---------------------------------------------------------------- util

    def dim_screen(self, alpha):
        overlay = pygame.Surface(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

    def blit(self, text, x, y, dim=False):
        color = cfg.COLOR_TEXT_DIM if dim else cfg.COLOR_TEXT
        self.screen.blit(self.font.render(text, True, color), (x, y))

    def run(self):
        while True:
            dt = self.clock.tick(cfg.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

    def quit(self):
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
