"""🕵️ CSI · 战术解剖报告：用真实事件流解释"为什么有效"（策划书 §5）。

报告里的每个数字都可由事件流复算；representative 回合的事件日志
与 tkinter 回放共用同一份数据（解释与肉眼可见的东西一致）。
"""

from __future__ import annotations

import random

from .court import NAMES, region_name
from .simulate import simulate


def analyze(genome, n: int = 24, seed: int = 99) -> dict:
    """跑 n 个回合（人盯人/联防交替），聚合战术特征。"""
    rng = random.Random(seed)
    table, source = None, None
    from .shot_model import get_table
    table, source = get_table()
    results = []
    for i in range(n):
        results.append(simulate(genome, "man" if i % 2 == 0 else "zone",
                                rng, table))

    made = [r for r in results if r.outcome.startswith("make")]
    ppp = sum(r.pts for r in results) / len(results)
    shot_events = [(r, e) for r in results for e in r.events if e.kind == "shot"]
    screen_events = [e for r in results for e in r.events if e.kind == "screen"]
    passes = [e for r in results for e in r.events if e.kind == "pass"]

    regions: dict[str, int] = {}
    for r, _e in shot_events:
        name = region_name(r.shot_pos)
        regions[name] = regions.get(name, 0) + 1

    avg_def = sum(e.data["def_dist"] for _r, e in shot_events) / max(1, len(shot_events))
    avg_shot_dist = sum(e.data["dist"] for _r, e in shot_events) / max(1, len(shot_events))
    screens_per_poss = len(screen_events) / max(1, len(results))
    avg_passes = len(passes) / max(1, len(results))

    # 防守消耗：帧数据累计防守人位移
    travel = 0.0
    for r in results:
        for (_t0, _a0, d0, _h, _o), (_t1, _a1, d1, _h2, _o2) in zip(r.frames, r.frames[1:]):
            for i in range(5):
                travel += ((d1[i][0] - d0[i][0]) ** 2
                           + (d1[i][1] - d0[i][1]) ** 2) ** 0.5
    travel_per_poss = travel / max(1, len(results))

    by_def = {"man": [], "zone": []}
    for i, r in enumerate(results):
        by_def["man" if i % 2 == 0 else "zone"].append(r.pts)

    rep = next((r for r in results if r.outcome.startswith("make")),
               results[0] if results else None)

    return dict(n=len(results), ppp=ppp,
                make_rate=len(made) / max(1, len(results)),
                ppp_man=sum(by_def["man"]) / max(1, len(by_def["man"])),
                ppp_zone=sum(by_def["zone"]) / max(1, len(by_def["zone"])),
                regions=regions, avg_def=avg_def, avg_shot_dist=avg_shot_dist,
                screens_per_poss=screens_per_poss, avg_passes=avg_passes,
                travel_per_poss=travel_per_poss, source=source,
                representative=rep, results=results)


def report(genome, n: int = 24, seed: int = 99) -> tuple[str, dict]:
    data = analyze(genome, n=n, seed=seed)
    lines = ["═" * 58,
             "═══ CSI · TACTIC 解剖报告 ═══",
             f"样本 {data['n']} 回合 · 命中率 {data['make_rate']:.0%} · "
             f"ppp {data['ppp']:.2f} · 人盯人 {data['ppp_man']:.2f} / "
             f"联防 {data['ppp_zone']:.2f}",
             f"战术: {genome.describe()} · 射手 {NAMES[genome.shooter]}",
             "─" * 58,
             "为什么有效："]
    reg_str = " / ".join(f"{k} {v}" for k, v in
                         sorted(data["regions"].items(), key=lambda kv: -kv[1]))
    lines.append(f"• 射手终结点: {reg_str or '—'}"
                 f"（平均出手 {data['avg_shot_dist']:.1f} m，"
                 f"平均防守距离 {data['avg_def']:.2f} m）")
    lines.append(f"• 掩护 {data['screens_per_poss']:.1f} 次/回合"
                 f"（被延缓的防守人给射手制造出手空间）")
    lines.append(f"• 平均传球 {data['avg_passes']:.1f} 次 → "
                 f"防守总位移 {data['travel_per_poss']:.1f} m/回合（消耗）")
    lines.append(f"• 命中模型: {data['source']}")
    rep = data["representative"]
    if rep is not None:
        lines.append("─" * 58)
        outcome_txt = {"make2": "✓ 命中(2分)", "make3": "✓ 命中(3分)",
                       "miss": "✗ 打铁", "violation": "✗ 8秒违例"}.get(rep.outcome, "")
        lines.append(f"代表性回合（{outcome_txt}）· tkinter 可回放同一事件流:")
        for e in rep.events:
            lines.append(f"  t={e.t:4.1f}  {e.text}")
    lines.append("═" * 58)
    return "\n".join(lines), data
