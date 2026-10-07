"""
Mana shop upgrades for Wizard Siege.

Four upgrades with scaling costs. Adding a new one means a new entry
in SHOP_UPGRADES and a matching key in settings.SHOP_COSTS.
"""

import settings as cfg


SHOP_UPGRADES = {
    "damage": {
        "name": "Arcane Power",
        "desc": "+5 bolt damage",
        "stat": "damage",
        "amount": 5,
        "max_level": 100,
    },
    "attack_spd": {
        "name": "Quickcast",
        "desc": "Cast speed -5%",
        "stat": "cooldown",
        "factor": 0.95,
        "floor": 0.08,
        "max_level": 100,
    },
    "max_hp": {
        "name": "Iron Ward",
        "desc": "+20 max health",
        "stat": "max_hp",
        "amount": 20,
        "max_level": 100,
    },
    "hp_regen": {
        "name": "Mending Sigil",
        "desc": "+1.5 hp/sec regen",
        "stat": "regen",
        "amount": 1.5,
        "max_level": 100,
    },
}


def cost(key, wizard):
    """Mana cost for the next level of this upgrade, or None if maxed."""
    level = wizard.upgrade_levels[key]
    costs = cfg.SHOP_COSTS[key]
    if level >= len(costs):
        return None
    return costs[level]


def can_afford(key, wizard):
    c = cost(key, wizard)
    return c is not None and wizard.mana >= c


def is_maxed(key, wizard):
    return wizard.upgrade_levels[key] >= SHOP_UPGRADES[key]["max_level"]


def apply(key, wizard):
    """Spend mana and apply the upgrade. Returns True on success."""
    if not can_afford(key, wizard) or is_maxed(key, wizard):
        return False

    c = cost(key, wizard)
    wizard.mana -= c
    wizard.upgrade_levels[key] += 1

    data = SHOP_UPGRADES[key]
    stat = data["stat"]

    if "factor" in data:
        value = getattr(wizard, stat) * data["factor"]
        if "floor" in data:
            value = max(data["floor"], value)
        setattr(wizard, stat, value)
    else:
        setattr(wizard, stat, getattr(wizard, stat) + data["amount"])

    # Heal the added HP immediately on max_hp upgrades
    if key == "max_hp":
        wizard.hp = min(wizard.hp + data["amount"], wizard.max_hp)

    return True
