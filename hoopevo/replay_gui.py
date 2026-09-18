"""战术回放动画：CSI 报告的"肉眼复核"通道。

回放与 CSI 报告读同一份事件流（策划书 §5：解释与肉眼可见的东西一致）。
"""

from __future__ import annotations

import math
import tkinter as tk

from .court import BASKET, NAMES, THREE_R, lerp

C_BG = "#0e1420"
C_FLOOR = "#a3763f"
C_LINE = "#7a5730"
C_ATK = "#ff9f43"
C_DEF = "#7fb3ff"
C_BALL = "#ffd479"
C_TEXT = "#e6edf3"
C_OPEN = "#7ce38b"

W, H = 640, 700
FPS = 12


class ReplayApp:
    def __init__(self, root: tk.Tk, result, title: str = ""):
        self.root = root
        self.frames = result.frames
        self.events = result.events
        self.title = title or "战术回放"
        self.frame_idx = 0
        self.playing = True

        root.title("HoopEvolution · 战术回放")
        self.canvas = tk.Canvas(root, width=W, height=H, bg=C_BG,
                                highlightthickness=0)
        self.canvas.pack()
        bar = tk.Frame(root, bg="#161d2b")
        bar.pack(fill="x")
        tk.Button(bar, text="⏯ 播放/暂停", command=self._toggle,
                  relief="flat", bg="#1b2430", fg=C_TEXT).pack(side="left",
                                                              padx=6, pady=4)
        tk.Button(bar, text="⏮ 上一回合", command=lambda: self._skip(-1),
                  relief="flat", bg="#1b2430", fg=C_TEXT).pack(side="left",
                                                              padx=6, pady=4)
        tk.Button(bar, text="下一回合 ⏭", command=lambda: self._skip(1),
                  relief="flat", bg="#1b2430", fg=C_TEXT).pack(side="left",
                                                              padx=6, pady=4)
        self.lbl = tk.Label(bar, text="", fg=C_TEXT, bg="#161d2b",
                            font=("Microsoft YaHei UI", 11))
        self.lbl.pack(side="left", padx=12)
        self.tick()

    # ---- 坐标：球场 y∈[-1.2,12.8] 映射到画布 ----
    def _px(self, x, y):
        sy = 46
        sx = 40
        scale = min((W - 2 * sx) / 15.0, (H - 2 * sy) / 14.0)
        ox = W / 2
        oy = H - sy - 0.2 * scale   # 底线在下方
        return ox + x * scale, oy - (y + 1.2) * scale

    def _toggle(self):
        self.playing = not self.playing

    def _skip(self, d):
        self.frame_idx = max(0, self.frame_idx + d * 10) % max(1, len(self.frames))

    def tick(self):
        if self.playing and self.frames:
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        self._draw()
        self.root.after(int(1000 / FPS), self.tick)

    def _current_event(self, t):
        shown = None
        for e in self.events:
            if e.t <= t + 0.05:
                shown = e
        return shown

    def _draw(self):
        cv = self.canvas
        cv.delete("all")
        if not self.frames:
            return
        t, atk, dfn, holder, opened = self.frames[self.frame_idx]
        # 地板
        cv.create_rectangle(0, H - 120, W, H, fill=C_FLOOR, outline="")
        bx, by = self._px(*BASKET)
        # 三分线
        pts = []
        for k in range(-90, 91, 6):
            a = math.radians(k)
            pts.append(self._px(THREE_R * math.sin(a), THREE_R * math.cos(a)))
        flat = [c for p in pts for c in p]
        cv.create_line(*flat, fill=C_LINE, width=2)
        cv.create_oval(bx - 5, by - 5, bx + 5, by + 5, fill=C_TEXT, outline="")
        # 球员
        for i, p in enumerate(atk):
            x, y = self._px(*p)
            r = 9
            color = C_BALL if i == holder else C_ATK
            cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
            cv.create_text(x, y - 16, text=NAMES[i], fill=C_TEXT,
                           font=("Consolas", 10, "bold"))
        for i, p in enumerate(dfn):
            x, y = self._px(*p)
            cv.create_oval(x - 8, y - 8, x + 8, y + 8, outline=C_DEF, width=3)
        # 球在持球人上方
        hx, hy = self._px(*atk[holder])
        cv.create_oval(hx - 4, hy - 14, hx + 4, hy - 6, fill=C_BALL, outline="")
        # 事件字幕
        ev = self._current_event(t)
        if ev is not None:
            cv.create_text(W / 2, 26, text=f"t={ev.t:4.1f}  {ev.text}",
                           fill=C_TEXT, font=("Microsoft YaHei UI", 12))
        if opened:
            cv.create_text(W / 2, 52, text="空 位 !", fill=C_OPEN,
                           font=("Microsoft YaHei UI", 14, "bold"))
        self.lbl.config(text=f"{self.title}  ·  帧 {self.frame_idx + 1}/{len(self.frames)}"
                             f"  t={t:.1f}s")


def replay(result, title: str = ""):
    root = tk.Tk()
    ReplayApp(root, result, title)
    root.mainloop()
