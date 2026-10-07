"""
Central config for Wizard Siege.

Tuning numbers and content definitions live here so balancing and adding
new enemies or spells stays a data change rather than a code change.
"""

# --- Screen ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900
FPS = 60
CAPTION = "Wizard Siege"

# --- Colors ---
COLOR_BG = (14, 12, 22)
COLOR_RUNE = (30, 26, 48)
COLOR_WIZARD = (120, 170, 255)
COLOR_WIZARD_CORE = (225, 240, 255)
COLOR_WARD = (70, 90, 150)
COLOR_BOLT = (180, 140, 255)
COLOR_TEXT = (235, 233, 245)
COLOR_TEXT_DIM = (150, 148, 170)
COLOR_HP_BG = (48, 18, 22)
COLOR_HP_FG = (205, 70, 80)
COLOR_WIZARD_HP = (90, 200, 130)
COLOR_MANA = (100, 180, 255)
COLOR_MANA_BG = (16, 24, 48)
COLOR_SHOP_BG = (18, 16, 32)
COLOR_SHOP_EDGE = (70, 60, 120)
COLOR_SHOP_HOVER = (45, 38, 80)
COLOR_CARD = (32, 28, 50)
COLOR_CARD_EDGE = (110, 90, 180)

# --- Wizard ---
WIZARD_MAX_HP = 120
WIZARD_RADIUS = 18
WIZARD_RANGE = 300
WIZARD_COOLDOWN = 0.50          # seconds between casts
WIZARD_DAMAGE = 14
WIZARD_REGEN = 0.0              # hp per second, raised by upgrades
WIZARD_MULTISHOT = 1            # targets struck per cast

# --- Bolts ---
BOLT_SPEED = 540                # pixels per second
BOLT_RADIUS = 5
BOLT_LIFETIME = 2.0
BOLT_PIERCE = 0                 # extra enemies hit after the first

# --- Mana ---
MANA_START = 0

# --- Shop upgrade costs (mana per level, index = current level bought) ---
def _cost_curve(base, growth, levels=100):
    """Generate a cost list that scales smoothly to 100 levels."""
    return [max(1, int(base + growth * i + (i ** 1.6) * 0.4)) for i in range(levels)]

SHOP_COSTS = {
    "damage":     _cost_curve(8,  4),
    "attack_spd": _cost_curve(10, 5),
    "max_hp":     _cost_curve(8,  4),
    "hp_regen":   _cost_curve(12, 6),
}

COLOR_LEVEL_BAR = (130, 80, 210)

# --- Enemies ---
# "unlock_at" is survival time in seconds before the type can spawn.
# "weight" controls relative spawn frequency once unlocked.
ENEMY_TYPES = {
    "goblin": {
        "name": "Goblin",
        "hp": 24,
        "speed": 78,
        "radius": 13,
        "damage": 7,
        "contact_cooldown": 0.8,
        "color": (110, 180, 90),
        "shape": "circle",
        "mana": 1,
        "weight": 10,
        "unlock_at": 0,
    },
    "wraith": {
        "name": "Wraith",
        "hp": 14,
        "speed": 145,
        "radius": 10,
        "damage": 5,
        "contact_cooldown": 0.5,
        "color": (150, 200, 235),
        "shape": "triangle",
        "mana": 2,
        "weight": 7,
        "unlock_at": 20,
    },
    "ogre": {
        "name": "Ogre",
        "hp": 120,
        "speed": 38,
        "radius": 23,
        "damage": 22,
        "contact_cooldown": 1.2,
        "color": (190, 110, 70),
        "shape": "square",
        "mana": 5,
        "weight": 4,
        "unlock_at": 45,
    },
    "revenant": {
        "name": "Revenant",
        "hp": 55,
        "speed": 62,
        "radius": 17,
        "damage": 12,
        "contact_cooldown": 0.9,
        "color": (200, 90, 200),
        "shape": "circle",
        "mana": 4,
        "weight": 5,
        "unlock_at": 75,
        # Splits into weaker enemies when killed.
        "on_death": {"kind": "goblin", "count": 2},
    },

    # --- World 1: Cursed Forest ---
    "thornling": {
        "name": "Thornling",
        "hp": 35,
        "speed": 95,
        "radius": 12,
        "damage": 9,
        "contact_cooldown": 0.6,
        "color": (80, 160, 60),
        "shape": "triangle",
        "mana": 2,
        "weight": 8,
        "unlock_at": 0,
    },
    "shade": {
        "name": "Shade",
        "hp": 20,
        "speed": 170,
        "radius": 9,
        "damage": 6,
        "contact_cooldown": 0.4,
        "color": (40, 60, 80),
        "shape": "triangle",
        "mana": 3,
        "weight": 5,
        "unlock_at": 30,
    },

    # --- World 2: Dungeon Depths ---
    "gargoyle": {
        "name": "Gargoyle",
        "hp": 180,
        "speed": 45,
        "radius": 22,
        "damage": 28,
        "contact_cooldown": 1.0,
        "color": (100, 95, 120),
        "shape": "square",
        "mana": 6,
        "weight": 4,
        "unlock_at": 0,
    },
    "bone_knight": {
        "name": "Bone Knight",
        "hp": 70,
        "speed": 55,
        "radius": 16,
        "damage": 18,
        "contact_cooldown": 0.8,
        "color": (220, 215, 190),
        "shape": "square",
        "mana": 5,
        "weight": 6,
        "unlock_at": 50,
    },

    # --- World 3: Volcanic Crater ---
    "magma_brute": {
        "name": "Magma Brute",
        "hp": 260,
        "speed": 35,
        "radius": 28,
        "damage": 35,
        "contact_cooldown": 1.4,
        "color": (200, 80, 20),
        "shape": "square",
        "mana": 8,
        "weight": 3,
        "unlock_at": 0,
    },
    "cinder_wisp": {
        "name": "Cinder Wisp",
        "hp": 18,
        "speed": 200,
        "radius": 8,
        "damage": 4,
        "contact_cooldown": 0.3,
        "color": (255, 140, 40),
        "shape": "circle",
        "mana": 2,
        "weight": 9,
        "unlock_at": 20,
    },

    # --- World 4: Astral Plane ---
    "void_stalker": {
        "name": "Void Stalker",
        "hp": 80,
        "speed": 130,
        "radius": 14,
        "damage": 22,
        "contact_cooldown": 0.5,
        "color": (140, 80, 255),
        "shape": "triangle",
        "mana": 7,
        "weight": 5,
        "unlock_at": 0,
    },
    "rift_horror": {
        "name": "Rift Horror",
        "hp": 400,
        "speed": 28,
        "radius": 32,
        "damage": 45,
        "contact_cooldown": 1.6,
        "color": (80, 20, 140),
        "shape": "circle",
        "mana": 12,
        "weight": 2,
        "unlock_at": 60,
        "on_death": {"kind": "void_stalker", "count": 3},
    },
}

# --- Spawning ---
SPAWN_INTERVAL_START = 1.4
SPAWN_INTERVAL_MIN = 0.32
SPAWN_RAMP_SECONDS = 120        # time to reach the fastest spawn rate
SPAWN_MARGIN = 60

# --- Level / progression ---
LEVEL_KILLS_BASE = 20           # kills needed to finish level 1
LEVEL_KILLS_GROWTH = 8          # extra kills required each level
BOSS_EVERY = 10                 # boss spawns every N levels

# --- Difficulty scaling per level ---
DIFF_HP_FACTOR = 0.10           # enemy HP +10% per level
DIFF_SPEED_FACTOR = 0.04        # enemy speed +4% per level
DIFF_SPAWN_FACTOR = 0.06        # spawn interval tightens 6% per level

# --- Juice ---
DAMAGE_NUMBER_LIFETIME = 0.7
DAMAGE_NUMBER_RISE = 40         # pixels risen over its lifetime
HIT_FLASH_TIME = 0.08
SHAKE_DECAY = 7.0

# --- Soul Shards ---
COLOR_SHARD = (220, 180, 255)
