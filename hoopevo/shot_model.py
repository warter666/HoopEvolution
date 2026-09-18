"""命中模型：从 shotlab 物理引擎标定"空位命中率-距离"曲线。

策划书 §6：物理即底座——不许拍脑袋写命中率。
shotlab（../BasketballPhysics）可用时：对 6 个距离锚点各跑 120 次
带执行噪声的蒙特卡洛；不可用时退化为文献表并在 source 里显式声明。
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ANCHORS = [2.0, 3.5, 5.0, 6.5, 7.5, 9.0]
FALLBACK = {2.0: 0.63, 3.5: 0.56, 5.0: 0.47, 6.5: 0.42, 7.5: 0.37, 9.0: 0.32}
MC_N = 120
SIGMA_V0 = 0.14
SIGMA_ANGLE = 0.9

_TABLE = None
_SOURCE = None


def _bootstrap_shotlab() -> bool:
    root = Path(__file__).resolve().parents[2] / "BasketballPhysics"
    if (root / "shotlab").exists():
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        return True
    return False


def _solve_v0(distance: float) -> float:
    """给定距离，找一个能把球送进筐心的 v0（49° 仰角，含阻力）。

    真空解析解热启动（×1.04 阻力修正），再在 ±0.75 内细扫取偏心最小者。
    """
    from shotlab.engine import Simulator
    from shotlab.params import ShotParams
    g, th = 9.81, math.radians(49.0)
    h, rim = 2.0, 3.05
    denom = 2.0 * math.cos(th) ** 2 * (h + distance * math.tan(th) - rim)
    if denom <= 0:
        return 8.0
    v0_center = math.sqrt(g * distance ** 2 / denom) * 1.04
    best, best_margin = None, 9.9
    for dv in [x * 0.15 for x in range(-5, 6)]:
        p = ShotParams(v0=round(v0_center + dv, 2), angle_deg=49.0,
                       release_height=h, distance=distance, spin=6.0)
        r = Simulator(p).run()
        if r.scored and r.crossed_rel is not None:
            margin = abs(r.crossed_rel)
            if margin < best_margin:
                best, best_margin = p.v0, margin
    return best if best else round(v0_center, 2)


def _calibrate() -> dict:
    from shotlab.engine import Simulator
    from shotlab.params import ShotParams
    rng = random.Random(2026)
    table = {}
    for d in ANCHORS:
        v0 = _solve_v0(d)
        hits = 0
        for _ in range(MC_N):
            p = ShotParams(v0=rng.gauss(v0, SIGMA_V0),
                           angle_deg=rng.gauss(49.0, SIGMA_ANGLE),
                           release_height=2.0, distance=d, spin=6.0)
            hits += Simulator(p).run().scored
        table[d] = hits / MC_N
    return table


def get_table() -> tuple[dict, str]:
    """惰性标定（缓存）。返回 (表, 来源说明)。"""
    global _TABLE, _SOURCE
    if _TABLE is not None:
        return _TABLE, _SOURCE
    if _bootstrap_shotlab():
        try:
            _TABLE = _calibrate()
            _SOURCE = "shotlab 物理引擎 Monte Carlo 标定（6 锚点 × 120 次）"
            return _TABLE, _SOURCE
        except Exception:
            pass
    _TABLE = dict(FALLBACK)
    _SOURCE = "文献回退表（shotlab 不可用）"
    return _TABLE, _SOURCE


def base_rate(dist: float, table: dict | None = None) -> float:
    """空位命中率：锚点线性插值，端点外平推。"""
    if table is None:
        table, _ = get_table()
    pts = sorted(table.items())
    if dist <= pts[0][0]:
        return pts[0][1]
    if dist >= pts[-1][0]:
        return pts[-1][1]
    for (d0, r0), (d1, r1) in zip(pts, pts[1:]):
        if d0 <= dist <= d1:
            k = (dist - d0) / (d1 - d0)
            return r0 + (r1 - r0) * k
    return pts[-1][1]


def p_make(dist: float, def_dist: float, table: dict | None = None) -> float:
    """出手命中概率 = 空位基线 × 防守距离调制（策划书 §6）。"""
    factor = min(1.2, max(0.6, 0.6 + 0.22 * def_dist))
    return min(0.93, max(0.02, base_rate(dist, table) * factor))
