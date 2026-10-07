# Wizard Siege

A top-down wizard survival game built in Python with pygame. You play a tower wizard holding off waves of monsters across five themed worlds, spending mana on upgrades mid-run and shards on permanent upgrades and new spells between runs.

## Features

- **12 enemy types** with distinct stats and behaviors (goblins, wraiths, ogres, revenants, and more), defined as data in `settings.py`
- **Boss fights** every 10 levels
- **5 worlds** (The Void, Cursed Forest, Dungeon Depths, Volcanic Crater, Astral Plane), each with its own background and unlock progression
- **Spell system** with base spells (Fireball, Ice Lance, Zephyr, Stone Wall) and a hybrid spell tree that combines them (Steam Burst, Blizzard, Landslide, Inferno, Arcane Singularity, and more)
- **Two upgrade layers**: in-run shop upgrades paid with mana, and a laboratory for permanent upgrades and spell mods paid with shards
- **Auto-targeting combat**, so play is about build decisions and timing rather than aim
- **Persistent progress** saved to a local JSON file

## Run it

Requires Python 3.10+.

```bash
git clone https://github.com/LordSerata/wizard-siege.git
cd wizard-siege
pip install -r requirements.txt
python main.py
```

## Controls

| Input | Action |
|-------|--------|
| Mouse | Navigate menus, laboratory, and shop |
| `Tab` or `U` | Open or close the in-run shop |
| `1` to `4` | Buy shop or laboratory options |
| `Tab` (laboratory) | Switch between permanent upgrades and spells |
| Mouse wheel | Scroll the spell list |
| `Esc` | Pause, or go back |
| `F11` | Toggle fullscreen |

## Code structure

| File | Responsibility |
|------|----------------|
| `main.py` | Game loop, state machine (title, laboratory, playing, boss fight, paused, dead), UI |
| `settings.py` | Central config: screen, colors, balance numbers, enemy definitions |
| `player.py` | Wizard stats, auto-targeting, casting |
| `enemy.py` | Enemy behaviors and rendering |
| `boss.py` | Boss logic |
| `waves.py` | Wave spawner |
| `spells.py` | Spell classes, projectiles, and the spell engine |
| `hybrid_tree.py` | Hybrid spell unlock tree |
| `upgrades.py` | In-run shop upgrades |
| `run_data.py` | Save/load and permanent progression |
| `worlds.py` | World definitions and animated backgrounds |
| `projectile.py`, `effects.py`, `gfx.py` | Bolts, damage numbers and screen shake, drawing helpers |

## Design notes

- Tuning numbers and content definitions live in `settings.py`, so adding an enemy or rebalancing is a data change instead of a code change.
- Each spell is its own class managed by a `SpellEngine`, so new spells plug in without touching the main loop.
- Game progress is stored in `save.json`, created on first run and ignored by git.

## Built with

Python, pygame-ce
