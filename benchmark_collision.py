"""Baseline benchmark: bolt collision cost vs enemy count.

Run from the wizard-siege folder:  python benchmark_collision.py
Run it again after the spatial grid is added and compare the numbers.
"""
import os
import random
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no window needed

from enemy import Enemy
from projectile import Bolt

random.seed(1)
N_BOLTS = 40
REPS = 20


def frame_cost_ms(n_enemies):
    enemies = [Enemy(random.uniform(0, 1200), random.uniform(0, 900), "goblin")
               for _ in range(n_enemies)]
    start = time.perf_counter()
    for _ in range(REPS):
        bolts = [Bolt((600, 450), random.choice(enemies), 14) for _ in range(N_BOLTS)]
        for bolt in bolts:
            bolt.update(1 / 60)
            bolt.check_hit(enemies)
    return (time.perf_counter() - start) / REPS * 1000


if __name__ == "__main__":
    print(f"{N_BOLTS} bolts per frame, collision only (60 FPS budget is 16.7 ms)")
    for n in (100, 500, 1000, 2000):
        print(f"{n:5d} enemies: {frame_cost_ms(n):6.2f} ms per frame")
