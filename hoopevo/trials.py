"""试炼挑战：给育种一个可读的终点。

三项固定试炼——大心脏 / 破联防 / 团队篮球——每项有明确的通过线。
育种不再是无目的的 ppp 数字爬升：读 CSI，定目标，雕战术，过试炼。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from .csi import analyze
from .shot_model import get_table
from .simulate import simulate

CLUTCH_WINDOW = (6.2, 7.6)
CLUTCH_RATE = 0.40
ZONE_PPP = 1.20
TEAM_PASSES = 2.0
TEAM_SCREENS = 1.5


@dataclass
class TrialResult:
    name: str
    passed: bool
    detail: str


def run_trials(genome, seed: int = 123, n: int = 12) -> list[TrialResult]:
    rng = random.Random(seed)
    table, _ = get_table()
    results = []

    # 一、大心脏：把出手时间压进压哨窗口，命中率仍要达标
    g = replace(genome, shot_time=min(CLUTCH_WINDOW[1],
                                      max(CLUTCH_WINDOW[0], genome.shot_time)))
    data = analyze(g, n=n, seed=seed + 1)
    results.append(TrialResult(
        f"大心脏（压哨 {CLUTCH_WINDOW[0]:.1f}~{CLUTCH_WINDOW[1]:.1f}s 出手，"
        f"命中率 ≥{CLUTCH_RATE:.0%}）",
        data["make_rate"] >= CLUTCH_RATE,
        f"命中率 {data['make_rate']:.0%}（{data['n']} 回合）"))

    # 二、破联防：联防下的每回合得分
    pts = [simulate(genome, "zone", rng, table).pts for _ in range(10)]
    ppp_zone = sum(pts) / len(pts)
    results.append(TrialResult(
        f"破联防（联防 ppp ≥{ZONE_PPP:.2f}）",
        ppp_zone >= ZONE_PPP,
        f"联防 ppp {ppp_zone:.2f}（10 回合，得 {sum(pts)} 分）"))

    # 三、团队篮球：球要动起来，人要动起来
    data2 = analyze(genome, n=n, seed=seed + 2)
    ok = (data2["avg_passes"] >= TEAM_PASSES
          and data2["screens_per_poss"] >= TEAM_SCREENS)
    results.append(TrialResult(
        f"团队篮球（传球 ≥{TEAM_PASSES:.1f} 次/回合 且 掩护 ≥{TEAM_SCREENS:.1f} 次/回合）",
        ok,
        f"传球 {data2['avg_passes']:.1f} · 掩护 {data2['screens_per_poss']:.1f}"))

    return results


def grade(results: list[TrialResult]) -> str:
    n = sum(1 for r in results if r.passed)
    return {3: "S", 2: "A", 1: "B", 0: "C"}.get(n, "C")
