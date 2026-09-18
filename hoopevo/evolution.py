"""进化引擎：锦标赛选择 + 精英保留 + 交叉/变异（策划书 §4）。

fitness = 人盯人 + 联防 双环境的每回合平均得分（ppp），同分取方差小者。
每个基因组的评估用独立子种子 → 完全可复现。
"""

from __future__ import annotations

import random

from . import tactics
from .simulate import run_batch


def _eval(genome, rng: random.Random, n_per_def: int, table) -> dict:
    stats = run_batch(genome, rng, n_per_def=n_per_def, table=table)
    stats["genome"] = genome
    return stats


def _sort_key(stats):
    return (-stats["ppp"], stats["var"])


def _tournament(scored, rng, k=3):
    best = None
    for _ in range(k):
        c = rng.choice(scored)
        if best is None or _sort_key(c) < _sort_key(best):
            best = c
    return best["genome"]


def evolve(pop_size=24, gens=12, seed=0, n_per_def=8, log=print):
    from .shot_model import get_table
    table, source = get_table()
    log(f"命中模型: {source}")
    rng = random.Random(seed)
    next_id = [0]

    def register(g):
        """创建时分配固定 tid：评估种子只由 tid 决定 →
        同基因组每代评估一致，精英保留真正生效（best 单调不降）。"""
        g.tid = next_id[0]
        next_id[0] += 1
        return g

    pop = [register(tactics.random_genome(rng)) for _ in range(pop_size)]
    history = []
    champion = None

    for gen in range(gens):
        scored = []
        for g in pop:
            sub = random.Random(seed * 100003 + g.tid * 97)
            stats = _eval(g, sub, n_per_def, table)
            scored.append(stats)
        scored.sort(key=_sort_key)
        best = scored[0]
        history.append(dict(gen=gen, best=best["ppp"], best_var=best["var"],
                            avg=sum(s["ppp"] for s in scored) / len(scored),
                            div=tactics.diversity(pop),
                            tactic_id=best["genome"].tid))
        champion = best
        log(f"Gen {gen:02d} · best {best['ppp']:.3f} ppp "
            f"(man {best['ppp_man']:.2f} / zone {best['ppp_zone']:.2f}) · "
            f"avg {history[-1]['avg']:.3f} · 多样性 {history[-1]['div']:.2f}")
        log(f"   TACTIC #{best['genome'].tid:04d}  {best['genome'].describe()}  "
            f"掩护 {best['screens']:.1f} 次/回合")

        if gen == gens - 1:
            break
        # 下一代：精英 4 + 锦标赛×交叉×变异
        elites = [s["genome"] for s in scored[:4]]
        offspring = list(elites)
        while len(offspring) < pop_size:
            p1 = _tournament(scored, rng)
            p2 = _tournament(scored, rng)
            child = tactics.mutate(tactics.crossover(p1, p2, rng), rng) \
                if rng.random() < 0.85 else tactics.mutate(p1, rng)
            offspring.append(register(child))
        pop = offspring

    return champion, history
