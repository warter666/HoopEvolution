"""半场几何：球篮在原点，y 正方向朝半场。"""

from __future__ import annotations

import math

BASKET = (0.0, 0.0)
THREE_R = 6.75          # 三分半径 m
X_MIN, X_MAX = -7.0, 7.0
Y_MIN, Y_MAX = -0.6, 12.0

NAMES = ["PG", "SG", "SF", "PF", "C"]
START_POS = [(-3.0, 8.0), (3.0, 8.5), (6.0, 5.0), (-6.0, 5.0), (0.0, 3.2)]


def dist_to_basket(p) -> float:
    return math.hypot(p[0] - BASKET[0], p[1] - BASKET[1])


def is_three(p) -> bool:
    return dist_to_basket(p) > THREE_R


def clamp_pos(p) -> tuple:
    return (min(X_MAX, max(X_MIN, p[0])), min(Y_MAX, max(Y_MIN, p[1])))


def region_name(p) -> str:
    d = dist_to_basket(p)
    if d < 2.2:
        return "篮下"
    theta = math.degrees(math.atan2(p[0], p[1]))  # 相对 +y（正面）的角度
    if d >= THREE_R:
        if theta < -50:
            return "左底角"
        if theta > 50:
            return "右底角"
        if abs(theta) <= 25:
            return "弧顶"
        return "左侧翼" if theta < 0 else "右侧翼"
    return "中距离"


def lerp(a, b, k):
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
