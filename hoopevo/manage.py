"""赛季模式：交互式战术育种——HoopEvolution 的可玩性核心。

你是战术主管，进化由你驾驶：
  * 每周自动考察全队（每战术人盯人+联防各 6 回合，结果有抽样噪声）
  * 每周 2 点行动点：重点考察（加样本降噪）/ 杂交 / 变异 / 淘汰换血 / 深度解剖
  * 10 周后选出一名冠军参加三项试炼
读报告、定方向、下决定——这就是玩法。
"""

from __future__ import annotations

import random
import statistics

from . import tactics
from .csi import report
from .shot_model import get_table
from .simulate import run_batch
from .trials import grade, run_trials

WEEKS = 10
AP_PER_WEEK = 2
STABLE_MAX = 6
SCOUT_N = 6      # 常规考察：每战术 2×6 回合
FOCUS_N = 14     # 重点考察：加 2×14 回合样本


class Manager:
    def __init__(self, seed: int = 0, weeks: int = WEEKS,
                 auto: bool = False, input_fn=input):
        self.rng = random.Random(seed)
        self.seed = seed
        self.weeks = weeks
        self.auto = auto
        self.input_fn = input_fn
        self.table, self.source = get_table()
        self.week = 1
        self.ap = AP_PER_WEEK
        self.stable: list[dict] = []
        self._tid = 0
        self._dissected_this_week = False

    # ------------------------------------------------------------------ 基础
    def _register(self, genome) -> dict:
        genome.tid = self._tid
        self._tid += 1
        entry = dict(genome=genome, ppps=[], screens=0.0, tid=genome.tid)
        self.stable.append(entry)
        return entry

    def _batch(self, genome, n: int) -> dict:
        sub = random.Random(self.seed * 7919 + genome.tid * 97 + self.week * 13
                            + len(self.stable))
        return run_batch(genome, sub, n_per_def=n, table=self.table)

    def _mean(self, entry) -> float:
        return statistics.mean(entry["ppps"]) if entry["ppps"] else 0.0

    def _std(self, entry) -> float:
        return statistics.pstdev(entry["ppps"]) if len(entry["ppps"]) > 1 else 9.9

    def _ask(self, prompt: str, valid: set) -> str:
        if self.auto:
            return sorted(valid)[0]
        while True:
            raw = self.input_fn(prompt).strip()
            if raw in valid:
                return raw
            print(f"  请输入 {'/'.join(sorted(valid))}")

    # ------------------------------------------------------------------ 每周流程
    def run(self) -> dict:
        print("═" * 60)
        print("  赛季模式 · 你是战术主管")
        print(f"  {self.weeks} 个训练周 · 每周 {AP_PER_WEEK} 行动点 · "
              f"队伍上限 {STABLE_MAX}")
        print(f"  终点：选出冠军参加三项试炼（大心脏/破联防/团队篮球）")
        print(f"  命中模型: {self.source}")
        print("═" * 60)
        for _ in range(2):
            self._register(tactics.random_genome(self.rng))

        for self.week in range(1, self.weeks + 1):
            self.ap = AP_PER_WEEK
            self._dissected_this_week = False
            self._scout_all()
            print(f"\n── 第 {self.week}/{self.weeks} 周 · 考察报告 ──")
            self._display()
            while self.ap > 0:
                self._action_menu()
        return self._final()

    def _scout_all(self):
        for e in self.stable:
            b = self._batch(e["genome"], SCOUT_N)
            e["ppps"].append(b["ppp"])
            e["screens"] = b["screens"]

    def _display(self):
        rows = sorted(self.stable, key=lambda e: -self._mean(e))
        for e in rows:
            g = e["genome"]
            print(f"  #{e['tid']:03d}  ppp {self._mean(e):.2f}"
                  f"±{self._std(e):.2f} (n={len(e['ppps'])}×{2 * SCOUT_N})"
                  f"  掩护 {e['screens']:.1f}/回合  {g.describe()}")

    def _pick_entry(self, action: str) -> dict | None:
        raw = self._ask(f"  {action} 哪支（输入编号，空格=取消）: ",
                        {str(e["tid"]) for e in self.stable} | {"s"})
        if raw == "s":
            return None
        return next(e for e in self.stable if e["tid"] == int(raw))

    # ------------------------------------------------------------------ 行动
    def _action_menu(self):
        if self.auto:
            self._auto_action()
            return
        print(f"\n  行动点 {self.ap}/2 —— "
              "[1]重点考察 [2]杂交 [3]变异 [4]淘汰换血 [5]深度解剖 [6]本周收工")
        c = self._ask("  选择: ", {"1", "2", "3", "4", "5", "6"})
        if c == "1":
            e = self._pick_entry("重点考察")
            if e is None:
                return
            b = self._batch(e["genome"], FOCUS_N)
            e["ppps"].append(b["ppp"])
            e["screens"] = b["screens"]
            self.ap -= 1
            print(f"  #{e['tid']:03d} 加训完成：样本增至 {len(e['ppps'])} 组，"
                  f"评估噪声 ±{self._std(e):.2f}")
        elif c == "2":
            if len(self.stable) >= STABLE_MAX:
                print("  队伍已满，先淘汰一支")
                return
            a = self._pick_entry("杂交父本")
            if a is None:
                return
            b = self._pick_entry("杂交母本")
            if b is None:
                return
            child = tactics.mutate(
                tactics.crossover(a["genome"], b["genome"], self.rng), self.rng)
            e = self._register(child)
            s = self._batch(e["genome"], SCOUT_N)
            e["ppps"].append(s["ppp"])
            e["screens"] = s["screens"]
            self.ap -= 1
            print(f"  杂交诞生 #{e['tid']:03d}  {e['genome'].describe()}")
        elif c == "3":
            if len(self.stable) >= STABLE_MAX:
                print("  队伍已满，先淘汰一支")
                return
            a = self._pick_entry("变异母本")
            if a is None:
                return
            child = tactics.mutate(a["genome"], self.rng)
            e = self._register(child)
            s = self._batch(e["genome"], SCOUT_N)
            e["ppps"].append(s["ppp"])
            e["screens"] = s["screens"]
            self.ap -= 1
            print(f"  变异诞生 #{e['tid']:03d}  {e['genome'].describe()}")
        elif c == "4":
            e = self._pick_entry("淘汰")
            if e is None:
                return
            self.stable.remove(e)
            fresh = self._register(tactics.random_genome(self.rng))
            s = self._batch(fresh["genome"], SCOUT_N)
            fresh["ppps"].append(s["ppp"])
            fresh["screens"] = s["screens"]
            self.ap -= 1
            print(f"  淘汰 #{e['tid']:03d}，新血 #{fresh['tid']:03d} 入队")
        elif c == "5":
            if self._dissected_this_week:
                print("  本周已深度解剖过一次")
                return
            e = self._pick_entry("深度解剖")
            if e is None:
                return
            text, _ = report(e["genome"], n=10, seed=self.seed + e["tid"])
            print(text)
            self._dissected_this_week = True
        elif c == "6":
            self.ap = 0
            print("  本周提前收工")

    def _auto_action(self):
        best = max(self.stable, key=self._mean)
        if len(self.stable) < STABLE_MAX and self.week > 1:
            child = tactics.mutate(
                tactics.crossover(best["genome"],
                                  self.rng.choice(self.stable)["genome"],
                                  self.rng), self.rng)
            e = self._register(child)
            s = self._batch(e["genome"], SCOUT_N)
            e["ppps"].append(s["ppp"])
            e["screens"] = s["screens"]
        else:
            b = self._batch(best["genome"], FOCUS_N)
            best["ppps"].append(b["ppp"])
        self.ap -= 1
        print(f"  （自动）消耗 1 AP，当前最优 #{best['tid']:03d}")

    # ------------------------------------------------------------------ 终局
    def _final(self) -> dict:
        print(f"\n{'═' * 60}")
        print("  赛季结束 —— 选出参加试炼的冠军战术")
        self._display()
        champ = max(self.stable, key=self._mean)
        if not self.auto:
            raw = self._ask(f"  派谁出战（编号，回车=默认 #{champ['tid']:03d}）: ",
                            {str(e["tid"]) for e in self.stable} | {""})
            if raw:
                champ = next(e for e in self.stable if e["tid"] == int(raw))
        print(f"  冠军：#{champ['tid']:03d}  {champ['genome'].describe()}")

        results = run_trials(champ["genome"], seed=self.seed * 31 + 7)
        print(f"\n{'─' * 60}\n  试炼结果：")
        for r in results:
            mark = "PASS" if r.passed else "FAIL"
            print(f"  [{mark}] {r.name}\n        {r.detail}")
        g = grade(results)
        print(f"\n  最终评级: {g}（{sum(1 for r in results if r.passed)}/3）")
        print("═" * 60)
        return dict(genome=champ["genome"], grade=g,
                    passed=sum(1 for r in results if r.passed),
                    results=results)
