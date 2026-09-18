"""战术基因组与遗传算子（策划书 §3）。"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from .court import X_MAX, X_MIN, Y_MAX, Y_MIN, clamp_pos, dist_to_basket

JITTER_XY = 0.8
JITTER_T = 0.5
BIG_IDS = (3, 4)   # PF / C


@dataclass
class Genome:
    routes: list          # 每人 2 个路标点 [(x, y, t), (x, y, t)]
    shooter: int
    shot_time: float
    tid: int = 0

    def describe(self) -> str:
        sp = self.routes[self.shooter][1]
        return (f"射手 {['PG','SG','SF','PF','C'][self.shooter]}"
                f"({sp[0]:+.1f},{sp[1]:.1f}) · shot {self.shot_time:.1f}s")


def _rand_wp(rng, player, big_in=False) -> tuple:
    if player in BIG_IDS and (big_in or rng.random() < 0.5):
        p = (rng.uniform(-3.5, 3.5), rng.uniform(0.8, 3.2))
    else:
        while True:
            p = (rng.uniform(X_MIN + 0.5, X_MAX - 0.5),
                 rng.uniform(1.0, 8.6))
            if 4.2 <= dist_to_basket(p) <= 8.0:
                break
    return p


def random_genome(rng: random.Random) -> Genome:
    shooter = rng.randrange(5)
    shot_time = rng.uniform(3.0, 7.0)
    routes = []
    for i in range(5):
        wps = []
        t1 = rng.uniform(1.0, 2.6)
        t2 = max(t1 + 0.8, rng.uniform(2.6, max(2.7, shot_time + 0.8)))
        wps.append((*_rand_wp(rng, i), round(t1, 2)))
        wps.append((*_rand_wp(rng, i, big_in=(i == shooter and False)),
                    round(t2, 2)))
        routes.append(wps)
    g = Genome(routes=routes, shooter=shooter, shot_time=round(shot_time, 2))
    return clamp_genome(g)


def clamp_genome(g: Genome) -> Genome:
    routes = []
    for wps in g.routes:
        pts = [(*clamp_pos((x, y)), max(0.3, t)) for x, y, t in wps]
        pts.sort(key=lambda p: p[2])
        routes.append(pts)
    shot_time = min(7.8, max(1.5, g.shot_time))
    return replace(g, routes=routes, shot_time=round(shot_time, 2))


def mutate(g: Genome, rng: random.Random) -> Genome:
    routes = [[(x, y, t) for x, y, t in wps] for wps in g.routes]
    for wps in routes:
        for i, (x, y, t) in enumerate(wps):
            if rng.random() < 0.75:
                wps[i] = (x + rng.gauss(0, JITTER_XY),
                          y + rng.gauss(0, JITTER_XY),
                          max(0.3, t + rng.gauss(0, JITTER_T)))
    shooter, shot_time = g.shooter, g.shot_time
    if rng.random() < 0.15:
        shooter = rng.randrange(5)
    if rng.random() < 0.75:
        shot_time = g.shot_time + rng.gauss(0, 0.6)
    if rng.random() < 0.15:
        i, j = rng.sample(range(5), 2)
        routes[i], routes[j] = routes[j], routes[i]
    return clamp_genome(Genome(routes=routes, shooter=shooter,
                               shot_time=shot_time))


def crossover(a: Genome, b: Genome, rng: random.Random) -> Genome:
    routes = [list(a.routes[i]) if rng.random() < 0.5 else list(b.routes[i])
              for i in range(5)]
    shooter = a.shooter if rng.random() < 0.5 else b.shooter
    shot_time = a.shot_time if rng.random() < 0.5 else b.shot_time
    return clamp_genome(Genome(routes=routes, shooter=shooter,
                               shot_time=shot_time))


def diversity(pop: list) -> float:
    """路标点坐标的平均标准差（粗粒度多样性）。"""
    if len(pop) < 2:
        return 0.0
    vals = []
    for g in pop:
        for wps in g.routes:
            for x, y, _t in wps:
                vals.append((x, y))
    n = len(vals)
    mx = sum(v[0] for v in vals) / n
    my = sum(v[1] for v in vals) / n
    var = sum((v[0] - mx) ** 2 + (v[1] - my) ** 2 for v in vals) / n
    return var ** 0.5
