"""
Hybrid spell tree data and nested-circle UI renderer.

Ring 1 — 4 base spells (already in spells.py / run_data.py)
Ring 2 — 4 hybrids, each needs 2 adjacent base spells
Ring 3 — 4 hybrids, each needs 2 adjacent ring-2 spells
Ring 4 — 1 ultimate, needs all 4 base spells
"""

import math
import pygame

# ------------------------------------------------------------------ tree data

# Each entry: id, name, desc, requires (list of spell ids), ring, cost
HYBRID_TREE = [
    # Ring 2
    {"id": "steam_burst",      "name": "Steam Burst",      "ring": 2, "cost": 200,
     "desc": "Scalding cloud — slows and burns nearby enemies",
     "requires": ["fireball", "ice_lance"]},
    {"id": "blizzard",         "name": "Blizzard",          "ring": 2, "cost": 200,
     "desc": "Wind scatters ice shards in all directions",
     "requires": ["ice_lance", "zephyr"]},
    {"id": "landslide",        "name": "Landslide",         "ring": 2, "cost": 200,
     "desc": "Wind hurls orbiting stones as projectiles",
     "requires": ["zephyr", "stone_wall"]},
    {"id": "volcanic_barrage", "name": "Volcanic Barrage",  "ring": 2, "cost": 200,
     "desc": "Stones erupt with lava on impact",
     "requires": ["stone_wall", "fireball"]},

    # Ring 3
    {"id": "maelstrom",  "name": "Maelstrom",  "ring": 3, "cost": 500,
     "desc": "Swirling storm of ice and steam",
     "requires": ["steam_burst", "blizzard"]},
    {"id": "avalanche",  "name": "Avalanche",  "ring": 3, "cost": 500,
     "desc": "Frozen boulder wave crushes everything",
     "requires": ["blizzard", "landslide"]},
    {"id": "earthquake", "name": "Earthquake", "ring": 3, "cost": 500,
     "desc": "Ground shockwave stuns and damages",
     "requires": ["landslide", "volcanic_barrage"]},
    {"id": "inferno",    "name": "Inferno",    "ring": 3, "cost": 500,
     "desc": "Persistent fire field that grows over time",
     "requires": ["volcanic_barrage", "steam_burst"]},

    # Ring 4
    {"id": "arcane_singularity", "name": "Arcane Singularity", "ring": 4, "cost": 1000,
     "desc": "Pulls enemies in then detonates in a massive explosion",
     "requires": ["maelstrom", "avalanche", "earthquake", "inferno"]},
]

# Flat lookup by id
HYBRID_BY_ID = {h["id"]: h for h in HYBRID_TREE}

# Base spell positions on ring 1 (angle on circle)
BASE_ANGLES = {
    "fireball":   math.pi * 1.75,   # top-right
    "ice_lance":  math.pi * 1.25,   # top-left
    "zephyr":     math.pi * 0.75,   # bottom-left
    "stone_wall": math.pi * 0.25,   # bottom-right
}


def _midpoint_angle(a1, a2):
    """Shortest-path midpoint between two angles, handling wrap-around."""
    diff = (a2 - a1 + math.pi) % (math.pi * 2) - math.pi
    return a1 + diff / 2


def _spell_angle(spell_id):
    """Angle for any spell — base or hybrid — computed from parents."""
    if spell_id in BASE_ANGLES:
        return BASE_ANGLES[spell_id]
    if spell_id == "arcane_singularity":
        return 0  # center, angle unused
    entry = HYBRID_BY_ID[spell_id]
    parent_angles = [_spell_angle(r) for r in entry["requires"]]
    # For 2 parents use midpoint; for more use average
    if len(parent_angles) == 2:
        return _midpoint_angle(parent_angles[0], parent_angles[1])
    return sum(parent_angles) / len(parent_angles)

BASE_COLORS = {
    "fireball":   (255, 140, 20),
    "ice_lance":  (140, 220, 255),
    "zephyr":     (160, 255, 180),
    "stone_wall": (180, 160, 120),
}

HYBRID_COLORS = {
    "steam_burst":       (200, 200, 80),
    "blizzard":          (100, 180, 255),
    "landslide":         (140, 120, 80),
    "volcanic_barrage":  (220, 100, 30),
    "maelstrom":         (80, 200, 220),
    "avalanche":         (180, 220, 255),
    "earthquake":        (160, 130, 80),
    "inferno":           (255, 80, 20),
    "arcane_singularity":(220, 160, 255),
}

ALL_SPELL_IDS = (
    ["fireball", "ice_lance", "zephyr", "stone_wall"] +
    [h["id"] for h in HYBRID_TREE]
)


def is_unlocked(spell_id, run_data):
    """Base spells check spells_owned; hybrids check hybrids_owned."""
    if spell_id in ["fireball", "ice_lance", "zephyr", "stone_wall"]:
        return spell_id in run_data.get("spells_owned", [])
    return spell_id in run_data.get("hybrids_owned", [])


def can_unlock(spell_id, run_data):
    """All requirements met and not already owned."""
    if is_unlocked(spell_id, run_data):
        return False
    entry = HYBRID_BY_ID.get(spell_id)
    if not entry:
        return False
    return all(is_unlocked(req, run_data) for req in entry["requires"])


def can_afford(spell_id, run_data):
    entry = HYBRID_BY_ID.get(spell_id)
    if not entry:
        return False
    return (can_unlock(spell_id, run_data) and
            run_data.get("shards", 0) >= entry["cost"])


def buy_hybrid(spell_id, run_data):
    import run_data as rd
    if not can_afford(spell_id, run_data):
        return False
    entry = HYBRID_BY_ID[spell_id]
    run_data["shards"] -= entry["cost"]
    run_data.setdefault("hybrids_owned", []).append(spell_id)
    # Ensure spell_mods entry exists for this hybrid
    if spell_id in rd.SPELL_MODS:
        run_data.setdefault("spell_mods", {})
        run_data["spell_mods"].setdefault(spell_id, {})
        for mod in rd.SPELL_MODS[spell_id]:
            run_data["spell_mods"][spell_id].setdefault(mod, 0)
    rd.save(run_data)
    return True


# ------------------------------------------------------------------ UI renderer

RING_RADII  = [0, 80, 148, 210, 265]   # radius for each ring
NODE_RADIUS = [0, 22,  20,  18,  26]   # node size per ring


def draw_tree(surface, cx, cy, run_data, hovered_id, font_sm, font_xs, t):
    """
    Draw the nested-circle hybrid tree centered at (cx, cy).
    Nodes sit at their computed midpoint angle — no connector lines.
    Returns {spell_id: pygame.Rect} for click detection.
    """
    hit_rects = {}

    # ---- Concentric ring circles ----
    for ring in range(1, 5):
        r = RING_RADII[ring]
        pygame.draw.circle(surface, (55, 46, 82), (cx, cy), r, 1)
        # Faint filled band between this ring and next
        if ring < 4:
            r_next = RING_RADII[ring + 1]
            band = pygame.Surface((r_next*2+2, r_next*2+2), pygame.SRCALPHA)
            pygame.draw.circle(band, (35, 28, 55, 25),
                               (r_next+1, r_next+1), r_next)
            pygame.draw.circle(band, (0, 0, 0, 0),
                               (r_next+1, r_next+1), r - 2)
            surface.blit(band, (cx - r_next - 1, cy - r_next - 1))

    # ---- Arcane Singularity glow (center) ----
    if is_unlocked("arcane_singularity", run_data):
        pulse = abs(math.sin(t * 1.2)) * 0.4 + 0.6
        col   = HYBRID_COLORS["arcane_singularity"]
        gs    = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, int(70 * pulse)), (40, 40), 38, 6)
        surface.blit(gs, (cx - 40, cy - 40))

    # Ring labels intentionally removed

    # ---- Base spells (ring 1) ----
    for bid in ["fireball", "ice_lance", "zephyr", "stone_wall"]:
        angle  = BASE_ANGLES[bid]
        nr     = NODE_RADIUS[1]
        nx     = int(cx + math.cos(angle) * RING_RADII[1])
        ny     = int(cy + math.sin(angle) * RING_RADII[1])
        owned  = is_unlocked(bid, run_data)
        hov    = (hovered_id == bid)
        col    = BASE_COLORS[bid]

        # Base spells always show as available (purchasable)
        _draw_node(surface, nx, ny, nr, col, owned, hov, t,
                   available=not owned)

        # Label only shown when owned (base spells always purchasable, show on owned)
        if owned:
            lx = nx + int(math.cos(angle) * (nr + 10))
            ly = ny + int(math.sin(angle) * (nr + 10))
            lbl = font_xs.render(bid.replace("_", " ").title(), True, col)
            surface.blit(lbl, lbl.get_rect(center=(lx, ly)))
        hit_rects[bid] = pygame.Rect(nx - nr, ny - nr, nr*2, nr*2)

    # ---- Hybrid nodes (rings 2 & 3) ----
    for hybrid in HYBRID_TREE:
        hid   = hybrid["id"]
        ring  = hybrid["ring"]
        if ring == 4:
            continue   # drawn separately as center node
        angle  = _spell_angle(hid)
        nr     = NODE_RADIUS[ring]
        nx     = int(cx + math.cos(angle) * RING_RADII[ring])
        ny     = int(cy + math.sin(angle) * RING_RADII[ring])
        owned  = is_unlocked(hid, run_data)
        avail  = can_unlock(hid, run_data)
        hov    = (hovered_id == hid)
        col    = HYBRID_COLORS[hid]

        _draw_node(surface, nx, ny, nr, col, owned,
                   hov and (owned or avail), t, available=avail)

        # Only show label when owned or available (hover alone not enough for locked)
        if owned or avail:
            lx = nx + int(math.cos(angle) * (nr + 10))
            ly = ny + int(math.sin(angle) * (nr + 10))
            lbl = font_xs.render(hybrid["name"], True,
                                 col if owned else (150, 140, 170))
            surface.blit(lbl, lbl.get_rect(center=(lx, ly)))
        hit_rects[hid] = pygame.Rect(nx - nr, ny - nr, nr*2, nr*2)

    # ---- Center: Arcane Singularity ----
    ult    = HYBRID_BY_ID["arcane_singularity"]
    nr     = NODE_RADIUS[4]
    owned  = is_unlocked("arcane_singularity", run_data)
    avail  = can_unlock("arcane_singularity", run_data)
    hov    = (hovered_id == "arcane_singularity")
    col    = HYBRID_COLORS["arcane_singularity"]
    _draw_node(surface, cx, cy, nr, col, owned,
               hov and (owned or avail), t, ultimate=True, available=avail)
    if owned or avail:
        lbl = font_xs.render("Arcane Singularity", True,
                             col if owned else (150, 140, 170))
        surface.blit(lbl, lbl.get_rect(center=(cx, cy + nr + 12)))
    hit_rects["arcane_singularity"] = pygame.Rect(cx-nr, cy-nr, nr*2, nr*2)

    return hit_rects


def _draw_node(surface, nx, ny, nr, col, owned, hovered, t,
               ultimate=False, available=False):
    """Draw a single spell node."""
    pulse = abs(math.sin(t * 1.8)) * 0.3 + 0.7

    if owned:
        gs = pygame.Surface((nr*4, nr*4), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, int(80 * pulse)),
                           (nr*2, nr*2), int(nr * 1.6))
        surface.blit(gs, (nx - nr*2, ny - nr*2))
        pygame.draw.circle(surface, col, (nx, ny), nr)
        pygame.draw.circle(surface, (255, 255, 255), (nx, ny), nr, 1)
        if ultimate:
            pygame.draw.circle(surface, col, (nx, ny), nr + 6, 2)
    elif hovered:
        pygame.draw.circle(surface, (40, 35, 60), (nx, ny), nr)
        pygame.draw.circle(surface, col, (nx, ny), nr, 2)
    elif available:
        # Pulsing border to indicate clickable
        pygame.draw.circle(surface, (25, 20, 38), (nx, ny), nr)
        border_alpha = int(120 + pulse * 80)
        gs = pygame.Surface((nr*2+2, nr*2+2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, border_alpha), (nr+1, nr+1), nr, 2)
        surface.blit(gs, (nx - nr - 1, ny - nr - 1))
    else:
        dark = tuple(max(0, v // 4) for v in col)
        pygame.draw.circle(surface, (22, 18, 34), (nx, ny), nr)
        pygame.draw.circle(surface, dark, (nx, ny), nr, 1)
