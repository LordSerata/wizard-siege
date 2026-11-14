"""Reproduces the save file problems found in run_data.py.

Run from the wizard-siege folder:  python verify_save_bugs.py
It uses a temporary save path, so your real save.json is never touched.
"""
import json
import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import run_data as rd

rd.SAVE_PATH = os.path.join(tempfile.mkdtemp(), "save.json")

print("1) Shared default bug (first run, no save file)")
data = rd.load()
data["shards"] = 10000
rd.buy_spell("fireball", data)
print("   module _DEFAULT spells_owned after buying:", rd._DEFAULT["spells_owned"])
os.remove(rd.SAVE_PATH)
print("   brand new load after deleting the save owns:", rd.load()["spells_owned"])

print("2) Corrupt save is silently replaced with a blank one")
with open(rd.SAVE_PATH, "w") as f:
    f.write("{not json")
print("   corrupt file loaded, shards =", rd.load()["shards"], "(no warning shown)")

print("3) Loaded data is never validated")
with open(rd.SAVE_PATH, "w") as f:
    json.dump({"shards": -5, "perm_levels": {"damage": 999}}, f)
loaded = rd.load()
print("   shards:", loaded["shards"], "| damage upgrade level:", loaded["perm_levels"]["damage"])
