"""5v5 半场回合模拟器（策划书 §2）。

位置型模拟，步长 0.05s，回合上限 8s。每次模拟产出完整事件流与
回放帧（CSI 报告与 tkinter 回放读同一份数据）。

防守两种环境：
  man  人盯人：每 0.3s 贪心指派，贴在"防守对象-球篮"连线上，
       反应延迟 0.25s（空位的来源），被掩护延缓时速度 ×0.4。
  zone 联防：5 个固定哨位，随球横向滑动。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .court import BASKET, NAMES, START_POS, dist_to_basket, is_three, region_name
from .shot_model import get_table, p_make

DT = 0.05
LIMIT = 8.0
ATT_SPEED = 3.2
DEF_SPEED = 5.0
REACT = 0.25
SCREEN_RADIUS = 0.6
DELAY_MULT, DELAY_TIME = 0.4, 0.8
PASS_GAIN = 0.5
PASS_RANGE = 9.0
ZONE_POSTS = [(-5.8, 3.4), (5.8, 3.4), (-2.2, 5.2), (2.2, 5.2), (0.0, 1.6)]


@dataclass
class Event:
    t: float
    kind: str      # pass / screen / shot / make / miss / violation / start
    text: str
    data: dict = field(default_factory=dict)


@dataclass
class PossessionResult:
    pts: int
    outcome: str            # make2 / make3 / miss / violation
    events: list
    frames: list            # (t, atk tuple, def tuple, holder, open_flag)
    shooter: int
    shot_pos: tuple
    def_dist: float
    screen_count: int
    delayed_at_shot: float


def _move(pos, target, speed, dt):
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    d = math.hypot(dx, dy)
    if d <= speed * dt or d < 1e-9:
        return target
    return (pos[0] + dx / d * speed * dt, pos[1] + dy / d * speed * dt)


def _nearest_def(pos, defenders) -> tuple:
    best_i, best_d = 0, 1e9
    for i, d in enumerate(defenders):
        dd = math.hypot(pos[0] - d[0], pos[1] - d[1])
        if dd < best_d:
            best_i, best_d = i, dd
    return best_i, best_d


def simulate(genome, defense: str, rng: random.Random,
             table: dict | None = None) -> PossessionResult:
    table = table or get_table()[0]
    atk = list(START_POS)
    wps = [list(w) for w in genome.routes]     # 每人待访问路标点队列
    targets = [tuple(wps[i][0][:2]) for i in range(5)]
    holders = 0                                # 持球人（=球的位置）
    events = [Event(0.0, "start",
                    f"{NAMES[0]}({atk[0][0]:+.1f},{atk[0][1]:.1f}) 发起", {})]
    frames = []
    delayed_until = [0.0] * 5                  # 人盯人下各防守人的延缓
    assign = list(range(5))                    # man: 防守人 i -> 进攻 assign[i]
    next_assign_t = 0.0
    next_screen_check = 0.0
    screen_count = 0
    defender_travel = [0.0] * 5
    defense = defense if defense in ("man", "zone") else "man"

    t = 0.0
    result_pts, outcome = 0, "violation"
    shot_pos, def_dist_final, delayed_at_shot = atk[genome.shooter], 0.0, 0.0
    frame_t = 0.0
    defenders_cache = list(ZONE_POSTS)   # 防守人初始站位（两种环境通用）

    while t <= LIMIT + 1e-9:
        # ---- 进攻跑位 ----
        for i in range(5):
            if wps[i]:
                atk[i] = _move(atk[i], targets[i], ATT_SPEED, DT)
                if math.hypot(targets[i][0] - atk[i][0],
                              targets[i][1] - atk[i][1]) < 0.15 or t >= wps[i][0][2]:
                    reached = wps[i].pop(0)
                    if wps[i]:
                        targets[i] = tuple(wps[i][0][:2])
                    if i == holders and reached is not None:
                        # 持球人到位 → 考虑传给空位最高的队友
                        _, hd = _nearest_def(atk[i], defenders_cache)
                        best_j, best_open = None, hd + PASS_GAIN
                        for j in range(5):
                            if j == i:
                                continue
                            _, jd = _nearest_def(atk[j], defenders_cache)
                            if jd > best_open and math.hypot(
                                    atk[i][0] - atk[j][0],
                                    atk[i][1] - atk[j][1]) < PASS_RANGE:
                                best_j, best_open = j, jd
                        if best_j is not None:
                            events.append(Event(
                                t, "pass",
                                f"传球 {NAMES[i]} → {NAMES[best_j]}"
                                f"（空位 {best_open:.1f} m）",
                                {"from": i, "to": best_j}))
                            holders = best_j

        # ---- 防守 ----
        prev_def = list(defenders_cache)
        if defense == "man":
            if t >= next_assign_t:
                assign = _greedy_assign(atk)
                next_assign_t = t + 0.3
            for d_i in range(5):
                mark = atk[assign[d_i]]
                d_out = math.hypot(mark[0], mark[1]) or 1.0
                target = (mark[0] - mark[0] / d_out * 0.9,
                          mark[1] - mark[1] / d_out * 0.9)
                speed = DEF_SPEED * (DELAY_MULT if t < delayed_until[d_i] else 1.0)
                new = _move(prev_def[d_i], target, speed, DT)
                defender_travel[d_i] += math.hypot(new[0] - prev_def[d_i][0],
                                                   new[1] - prev_def[d_i][1])
                defenders_cache[d_i] = new
        else:
            bx = atk[holders][0]
            for d_i in range(5):
                target = (ZONE_POSTS[d_i][0] + bx * 0.3, ZONE_POSTS[d_i][1])
                new = _move(prev_def[d_i], target, DEF_SPEED, DT)
                defender_travel[d_i] += math.hypot(new[0] - prev_def[d_i][0],
                                                   new[1] - prev_def[d_i][1])
                defenders_cache[d_i] = new

        # ---- 掩护判定：无球人贴近射手的防守人 → 延缓 ----
        if t >= next_screen_check:
            next_screen_check = t + 0.2
            if defense == "man":
                shooter_def = assign.index(genome.shooter)
            else:
                shooter_def, _ = _nearest_def(atk[genome.shooter], defenders_cache)
            if t < delayed_until[shooter_def]:
                pass
            else:
                for i in range(5):
                    if i == genome.shooter:
                        continue
                    dd = math.hypot(atk[i][0] - defenders_cache[shooter_def][0],
                                    atk[i][1] - defenders_cache[shooter_def][1])
                    if dd < SCREEN_RADIUS:
                        delayed_until[shooter_def] = t + DELAY_TIME
                        screen_count += 1
                        events.append(Event(
                            t, "screen",
                            f"{NAMES[i]} 掩护成立：{NAMES[genome.shooter]} 的防守人"
                            f"被延缓 {DELAY_TIME:.1f}s",
                            {"by": i, "defender": shooter_def}))
                        break

        # ---- 出手 ----
        if holders != genome.shooter and t >= genome.shot_time - 0.35:
            events.append(Event(t, "pass",
                                f"传球 {NAMES[holders]} → {NAMES[genome.shooter]}"
                                f"（终结输送）", {"from": holders, "to": genome.shooter}))
            holders = genome.shooter
        if holders == genome.shooter and t >= genome.shot_time:
            shot_pos = atk[genome.shooter]
            d_shooter, def_dist_final = _nearest_def(shot_pos, defenders_cache)
            delayed_at_shot = max(0.0, delayed_until[d_shooter] - t)
            dist = dist_to_basket(shot_pos)
            p = p_make(dist, def_dist_final, table)
            roll = rng.random()
            three = is_three(shot_pos)
            pts = 3 if three else 2
            outcome = ("make3" if three else "make2") if roll < p else "miss"
            result_pts = pts if roll < p else 0
            events.append(Event(
                t, "shot",
                f"{NAMES[genome.shooter]} {region_name(shot_pos)}出手 "
                f"{dist:.1f} m · 最近防守 {def_dist_final:.1f} m · "
                f"命中概率 {p:.2f} · 被延缓余量 {delayed_at_shot:.2f}s",
                {"dist": dist, "def_dist": def_dist_final, "p": p}))
            events.append(Event(t + 0.4, "make" if roll < p else "miss",
                                "✓ 命中" if roll < p else "✗ 打铁", {}))
            break

        t += DT
        if t >= frame_t:
            _, od = _nearest_def(atk[holders], defenders_cache)
            frames.append((round(t, 2), tuple(atk), tuple(defenders_cache),
                           holders, od > 2.2))
            frame_t += 0.1
        if t > LIMIT:
            events.append(Event(LIMIT, "violation", "8 秒违例", {}))
            outcome = "violation"
            break

    return PossessionResult(pts=result_pts, outcome=outcome, events=events,
                            frames=frames, shooter=genome.shooter,
                            shot_pos=shot_pos, def_dist=def_dist_final,
                            screen_count=screen_count,
                            delayed_at_shot=delayed_at_shot)


def _greedy_assign(atk) -> list:
    """贪心指派：依次为每个进攻者配一个未被占用的防守者（近似就近对位）。

    返回 permutation：assign[d] = 防守人 d 负责的进攻者编号。
    """
    free = list(range(5))
    picked = []
    for i in range(5):
        best, bd = free[0], 1e9
        for j in free:
            d = math.hypot(atk[i][0] - atk[j][0], atk[i][1] - atk[j][1]) \
                + (2.0 if j == i else 0.0)
            if d < bd:
                best, bd = j, d
        picked.append(best)
        free.remove(best)
    # picked[i] 是进攻者 i 的对位防守人；转置为 防守人 -> 进攻者
    assign = [0] * 5
    for attacker_i, defender_j in enumerate(picked):
        assign[defender_j] = attacker_i
    return assign


def run_batch(genome, rng: random.Random, n_per_def: int = 8,
              table: dict | None = None) -> dict:
    """双环境评估：人盯人 + 联防各 n_per_def 回合。"""
    table = table or get_table()[0]
    pts = {"man": [], "zone": []}
    sample = None
    screens = 0
    for defense in ("man", "zone"):
        for k in range(n_per_def):
            r = simulate(genome, defense, rng, table)
            pts[defense].append(r.pts)
            screens += r.screen_count
            if r.outcome.startswith("make") and sample is None:
                sample = r
    total = pts["man"] + pts["zone"]
    ppp = sum(total) / len(total)
    var = (sum((x - ppp) ** 2 for x in total) / len(total)) ** 0.5
    return dict(ppp=ppp, ppp_man=sum(pts["man"]) / len(pts["man"]),
                ppp_zone=sum(pts["zone"]) / len(pts["zone"]),
                var=var, screens=screens / (2 * n_per_def), sample=sample)
