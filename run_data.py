"""
Persistent run data — Soul Shards and permanent starting buffs.

Saved to a simple JSON file next to the game so it survives between
sessions. If the file is missing or corrupt it starts fresh.
"""

import json
import os

SAVE_PATH = os.path.join(os.path.dirname(__file__), "save.json")

SPELL_NAMES = {
    "fireball":   "Fireball",
    "ice_lance":  "Ice Lance",
    "zephyr":     "Zephyr",
    "stone_wall": "Stone Wall",
}

SPELL_DESCS = {
    "fireball":   "Kills trigger chain explosions dealing splash damage",
    "ice_lance":  "Bolts freeze enemies; frozen enemies shatter for bonus damage",
    "zephyr":     "Periodic wind burst pushes and damages nearby enemies",
    "stone_wall": "Orbiting stones crush enemies and respawn over time",
}

SPELL_BASE_COST = 100
SPELL_COST_STEP = 150

def _mod_curve(base, growth, levels=100):
    return [max(1, int(base + growth * i + (i ** 1.4) * 0.2)) for i in range(levels)]

# Modifiers for each spell — 4 per spell, each upgradeable to level 100
SPELL_MODS = {
    "fireball": {
        "radius":   {"name": "Blast Radius",   "desc": "+15 explosion radius",     "costs": _mod_curve(3, 3)},
        "chance":   {"name": "Ignition Chance","desc": "+7% trigger chance",        "costs": _mod_curve(4, 4)},
        "damage":   {"name": "Inferno",        "desc": "+8 splash damage",          "costs": _mod_curve(3, 3)},
        "chains":   {"name": "Chain Reaction", "desc": "+1 chain explosion",        "costs": _mod_curve(8, 8)},
    },
    "ice_lance": {
        "slow_dur":      {"name": "Deep Freeze",   "desc": "+0.5s freeze duration",   "costs": _mod_curve(3, 3)},
        "slow_amount":   {"name": "Permafrost",    "desc": "+6% slow strength",       "costs": _mod_curve(3, 3)},
        "shatter_mul":   {"name": "Shatter",       "desc": "+0.4x shatter damage",    "costs": _mod_curve(5, 5)},
        "freeze_chance": {"name": "Brittle Cold",  "desc": "+8% freeze chance",       "costs": _mod_curve(4, 4)},
    },
    "zephyr": {
        "push_force":  {"name": "Gale Force",   "desc": "+60 push force",            "costs": _mod_curve(3, 3)},
        "push_radius": {"name": "Eye of Storm", "desc": "+20 push radius",           "costs": _mod_curve(3, 3)},
        "push_cd":     {"name": "Updraft",      "desc": "-0.1s push cooldown",       "costs": _mod_curve(4, 4)},
        "push_damage": {"name": "Wind Shear",   "desc": "+4 push damage",            "costs": _mod_curve(3, 3)},
    },
    "stone_wall": {
        "stone_hp":    {"name": "Granite",      "desc": "+15 stone HP",              "costs": _mod_curve(3, 3)},
        "stone_count": {"name": "Rampart",      "desc": "+1 orbiting stone",         "costs": _mod_curve(6, 6)},
        "spawn_cd":    {"name": "Quarry",       "desc": "-0.6s respawn time",        "costs": _mod_curve(4, 4)},
        "contact_dmg": {"name": "Crushing Blow","desc": "+6 contact damage",         "costs": _mod_curve(3, 3)},
    },

    # ---- Hybrid spell mods ----
    "steam_burst": {
        "cloud_size":   {"name": "Scalding Radius", "desc": "+15 cloud radius",       "costs": _mod_curve(5, 5)},
        "cloud_dur":    {"name": "Lingering Heat",  "desc": "+0.5s cloud duration",   "costs": _mod_curve(4, 4)},
        "burn_dmg":     {"name": "Searing",         "desc": "+2 burn damage/sec",     "costs": _mod_curve(4, 4)},
        "slow_power":   {"name": "Steam Chill",     "desc": "+5% slow strength",      "costs": _mod_curve(4, 4)},
    },
    "blizzard": {
        "shard_count":  {"name": "Ice Storm",       "desc": "+2 shards per burst",    "costs": _mod_curve(6, 6)},
        "shard_dmg":    {"name": "Frostbite",       "desc": "+5 shard damage",        "costs": _mod_curve(4, 4)},
        "shard_speed":  {"name": "Arctic Wind",     "desc": "+60 shard speed",        "costs": _mod_curve(3, 3)},
        "freeze_dur":   {"name": "Deep Blizzard",   "desc": "+0.4s freeze duration",  "costs": _mod_curve(4, 4)},
    },
    "landslide": {
        "stone_count":  {"name": "Boulder Barrage", "desc": "+1 stone per volley",    "costs": _mod_curve(6, 6)},
        "stone_dmg":    {"name": "Crushing Weight", "desc": "+10 impact damage",      "costs": _mod_curve(4, 4)},
        "stone_speed":  {"name": "Swift Stones",    "desc": "+40 stone speed",        "costs": _mod_curve(3, 3)},
        "cooldown":     {"name": "Aftershock",      "desc": "-0.2s cooldown",         "costs": _mod_curve(4, 4)},
    },
    "volcanic_barrage": {
        "lava_radius":  {"name": "Magma Splash",    "desc": "+10 explosion radius",   "costs": _mod_curve(4, 4)},
        "lava_dmg":     {"name": "Incendiary",      "desc": "+8 explosion damage",    "costs": _mod_curve(4, 4)},
        "fire_rate":    {"name": "Rapid Fire",      "desc": "-0.2s cooldown",         "costs": _mod_curve(4, 4)},
        "chain_lava":   {"name": "Chain Eruption",  "desc": "+1 chain explosion",     "costs": _mod_curve(7, 7)},
    },
    "maelstrom": {
        "storm_radius": {"name": "Eye Expansion",   "desc": "+20 storm radius",       "costs": _mod_curve(5, 5)},
        "storm_dmg":    {"name": "Tempest Force",   "desc": "+4 damage/sec",          "costs": _mod_curve(4, 4)},
        "slow_power":   {"name": "Frozen Gale",     "desc": "+8% slow strength",      "costs": _mod_curve(4, 4)},
        "cooldown":     {"name": "Perpetual Storm", "desc": "-0.4s cooldown",         "costs": _mod_curve(5, 5)},
    },
    "avalanche": {
        "boulder_count":{"name": "Rock Slide",      "desc": "+2 boulders per wave",   "costs": _mod_curve(6, 6)},
        "boulder_dmg":  {"name": "Glacial Force",   "desc": "+15 boulder damage",     "costs": _mod_curve(4, 4)},
        "slow_power":   {"name": "Deep Freeze",     "desc": "+10% slow strength",     "costs": _mod_curve(4, 4)},
        "cooldown":     {"name": "Relentless",      "desc": "-0.5s cooldown",         "costs": _mod_curve(5, 5)},
    },
    "earthquake": {
        "wave_radius":  {"name": "Richter Scale",   "desc": "+40 shockwave radius",   "costs": _mod_curve(5, 5)},
        "wave_dmg":     {"name": "Ground Shatter",  "desc": "+15 wave damage",        "costs": _mod_curve(4, 4)},
        "wave_count":   {"name": "Aftershocks",     "desc": "+1 wave per quake",      "costs": _mod_curve(7, 7)},
        "cooldown":     {"name": "Tectonic",        "desc": "-0.6s cooldown",         "costs": _mod_curve(5, 5)},
    },
    "inferno": {
        "field_size":   {"name": "Wildfire",        "desc": "+20 max field radius",   "costs": _mod_curve(5, 5)},
        "burn_dmg":     {"name": "Hellfire",        "desc": "+4 burn damage/sec",     "costs": _mod_curve(4, 4)},
        "field_dur":    {"name": "Eternal Flame",   "desc": "+1s field duration",     "costs": _mod_curve(4, 4)},
        "field_count":  {"name": "Conflagration",   "desc": "+1 simultaneous field",  "costs": _mod_curve(8, 8)},
    },
    "arcane_singularity": {
        "pull_force":   {"name": "Event Horizon",   "desc": "+40 pull force",         "costs": _mod_curve(5, 5)},
        "blast_dmg":    {"name": "Supernova",       "desc": "+50 detonation damage",  "costs": _mod_curve(5, 5)},
        "pull_dur":     {"name": "Singularity",     "desc": "+0.5s pull duration",    "costs": _mod_curve(5, 5)},
        "cooldown":     {"name": "Cosmic Tide",     "desc": "-1s cooldown",           "costs": _mod_curve(6, 6)},
    },
}

# Starting buff costs in Soul Shards (index = level already purchased)
def _perm_curve(base, growth, levels=100):
    return [max(1, int(base + growth * i + (i ** 1.5) * 0.3)) for i in range(levels)]

PERM_COSTS = {
    "damage":     _perm_curve(2, 2),
    "attack_spd": _perm_curve(3, 3),
    "max_hp":     _perm_curve(2, 2),
    "hp_regen":   _perm_curve(3, 3),
}

# How much each level of a permanent buff adds to the starting stat
PERM_BONUS = {
    "damage":     5,
    "attack_spd": 0.88,   # factor on cooldown (applied per level bought)
    "max_hp":     20,
    "hp_regen":   1.0,
}

PERM_NAMES = {
    "damage":     "Dark Power",
    "attack_spd": "Swiftweave",
    "max_hp":     "Blood Ward",
    "hp_regen":   "Lifetap",
}

PERM_DESCS = {
    "damage":     "+5 starting damage",
    "attack_spd": "Cast speed -12% per level",
    "max_hp":     "+20 starting max HP",
    "hp_regen":   "+1 starting HP/sec regen",
}

def _default_spell_mods():
    return {spell: {mod: 0 for mod in mods}
            for spell, mods in SPELL_MODS.items()}

_DEFAULT = {
    "shards":         0,
    "perm_levels":    {k: 0 for k in PERM_COSTS},
    "spells_owned":   [],
    "spell_mods":     _default_spell_mods(),
    "hybrids_owned":  [],
    "best_level":     0,
    "total_runs":     0,
    "current_world":  0,
    "highest_world":  0,
}


def load():
    try:
        with open(SAVE_PATH) as f:
            data = json.load(f)
        # Backfill any missing keys from a future version
        for k, v in _DEFAULT.items():
            data.setdefault(k, v)
        data["perm_levels"].setdefault("hp_regen", 0)
        data.setdefault("spells_owned", [])
        data.setdefault("hybrids_owned", [])
        data.setdefault("spell_mods", _default_spell_mods())
        for spell, mods in SPELL_MODS.items():
            data["spell_mods"].setdefault(spell, {})
            for mod in mods:
                data["spell_mods"][spell].setdefault(mod, 0)
        # Also init hybrid spell mod entries if missing
        from hybrid_tree import HYBRID_TREE
        for h in HYBRID_TREE:
            hid = h["id"]
            if hid in SPELL_MODS:
                data["spell_mods"].setdefault(hid, {})
                for mod in SPELL_MODS[hid]:
                    data["spell_mods"][hid].setdefault(mod, 0)
        return data
    except Exception:
        return dict(_DEFAULT)


def save(data):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def perm_cost(key, data):
    level = data["perm_levels"][key]
    costs = PERM_COSTS[key]
    if level >= len(costs):
        return None
    return costs[level]


def perm_maxed(key, data):
    return data["perm_levels"][key] >= 100


def can_afford_perm(key, data):
    c = perm_cost(key, data)
    return c is not None and data["shards"] >= c


def buy_perm(key, data):
    if not can_afford_perm(key, data):
        return False
    data["shards"] -= perm_cost(key, data)
    data["perm_levels"][key] += 1
    save(data)
    return True


def apply_perms_to_wizard(wizard, data):
    """Apply all purchased permanent buffs to a fresh wizard."""
    for key, level in data["perm_levels"].items():
        if level == 0:
            continue
        if key == "damage":
            wizard.damage += PERM_BONUS["damage"] * level
        elif key == "attack_spd":
            for _ in range(level):
                wizard.cooldown = max(0.10, wizard.cooldown * PERM_BONUS["attack_spd"])
        elif key == "max_hp":
            bonus = PERM_BONUS["max_hp"] * level
            wizard.max_hp += bonus
            wizard.hp += bonus
        elif key == "hp_regen":
            wizard.regen += PERM_BONUS["hp_regen"] * level


def shards_for_level(level_reached):
    """Soul Shards rewarded for reaching a given level this run."""
    if level_reached < 1:
        return 0
    return max(1, level_reached // 2)


def spell_cost(key, data):
    """Cost to buy this spell. Increases with each spell already owned."""
    if key in data["spells_owned"]:
        return None   # already owned
    owned = len(data["spells_owned"])
    return SPELL_BASE_COST + owned * SPELL_COST_STEP


def spell_owned(key, data):
    return key in data.get("spells_owned", []) or key in data.get("hybrids_owned", [])


def can_afford_spell(key, data):
    if spell_owned(key, data):
        return False
    c = spell_cost(key, data)
    return c is not None and data["shards"] >= c


def buy_spell(key, data):
    if not can_afford_spell(key, data):
        return False
    data["shards"] -= spell_cost(key, data)
    data["spells_owned"].append(key)
    # Ensure spell_mods entry exists
    data.setdefault("spell_mods", {})
    data["spell_mods"].setdefault(key, {})
    for mod in SPELL_MODS.get(key, {}):
        data["spell_mods"][key].setdefault(mod, 0)
    save(data)
    return True


def apply_spells_to_wizard(wizard, data):
    """Mark which spells are active on the wizard for the game to use."""
    wizard.spells = list(data["spells_owned"])


def spell_mod_cost(spell_key, mod_key, data):
    level = data["spell_mods"][spell_key][mod_key]
    costs = SPELL_MODS[spell_key][mod_key]["costs"]
    if level >= len(costs):
        return None
    return costs[level]


def spell_mod_maxed(spell_key, mod_key, data):
    return data["spell_mods"][spell_key][mod_key] >= 100


def can_afford_spell_mod(spell_key, mod_key, data):
    if not spell_owned(spell_key, data):
        return False
    c = spell_mod_cost(spell_key, mod_key, data)
    return c is not None and data["shards"] >= c


def buy_spell_mod(spell_key, mod_key, data):
    if not can_afford_spell_mod(spell_key, mod_key, data):
        return False
    data["shards"] -= spell_mod_cost(spell_key, mod_key, data)
    data["spell_mods"][spell_key][mod_key] += 1
    save(data)
    return True


def reset(data):
    import copy
    fresh = copy.deepcopy(_DEFAULT)
    fresh["spell_mods"]  = _default_spell_mods()
    fresh["perm_levels"] = {k: 0 for k in PERM_COSTS}
    fresh["spells_owned"] = []
    data.clear()
    data.update(fresh)
    save(data)
