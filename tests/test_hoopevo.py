"""HoopEvolution 测试：基因组算子 / 模拟器不变量 / 进化单调性 / CSI 报告。"""

import unittest

from hoopevo import tactics
from hoopevo.court import X_MAX, X_MIN, Y_MAX, Y_MIN, region_name
from hoopevo.csi import report
from hoopevo.evolution import evolve
from hoopevo.shot_model import FALLBACK, base_rate, get_table, p_make
from hoopevo.simulate import run_batch, simulate

FAST_TABLE = dict(FALLBACK)


class TestShotModel(unittest.TestCase):
    def test_table_source_declared(self):
        _table, source = get_table()
        self.assertTrue("shotlab" in source or "回退" in source, msg=source)

    def test_base_rate_interpolation(self):
        t = dict(FALLBACK)
        self.assertAlmostEqual(base_rate(2.0, t), FALLBACK[2.0])
        mid = base_rate(2.75, t)
        self.assertAlmostEqual(mid, (FALLBACK[2.0] + FALLBACK[3.5]) / 2, places=2)
        self.assertEqual(base_rate(20.0, t), FALLBACK[9.0])

    def test_defender_modulation_bounds(self):
        open_p = p_make(5.0, 3.0, FAST_TABLE)
        tight = p_make(5.0, 0.2, FAST_TABLE)
        self.assertGreater(open_p, tight)
        self.assertLessEqual(open_p, 0.93)
        self.assertGreaterEqual(tight, 0.02)


class TestGenome(unittest.TestCase):
    def test_random_genome_valid(self):
        rng = __import__("random").Random(0)
        g = tactics.random_genome(rng)
        for wps in g.routes:
            for x, y, t in wps:
                self.assertTrue(X_MIN <= x <= X_MAX)
                self.assertTrue(Y_MIN <= y <= Y_MAX)
                self.assertGreaterEqual(t, 0.3)
        self.assertTrue(1.5 <= g.shot_time <= 7.8)

    def test_mutate_keeps_bounds(self):
        rng = __import__("random").Random(1)
        g = tactics.random_genome(rng)
        for _ in range(20):
            m = tactics.mutate(g, rng)
            for wps in m.routes:
                for x, y, _t in wps:
                    self.assertTrue(X_MIN - 1e-6 <= x <= X_MAX + 1e-6)
                    self.assertTrue(Y_MIN - 1e-6 <= y <= Y_MAX + 1e-6)

    def test_crossover_mixes_parents(self):
        rng = __import__("random").Random(2)
        a = tactics.random_genome(rng)
        b = tactics.random_genome(rng)
        c = tactics.crossover(a, b, rng)
        same = sum(1 for i in range(5) if c.routes[i] == a.routes[i])
        self.assertLess(same, 5)  # 至少从 b 继承了一条路线（概率性，5条全同概率1/32）


class TestSimulate(unittest.TestCase):
    def test_deterministic(self):
        import random
        g = tactics.random_genome(random.Random(3))
        r1 = simulate(g, "man", random.Random(5), FAST_TABLE)
        r2 = simulate(g, "man", random.Random(5), FAST_TABLE)
        self.assertEqual((r1.pts, r1.outcome, len(r1.frames)),
                         (r2.pts, r2.outcome, len(r2.frames)))

    def test_outcome_and_events(self):
        import random
        g = tactics.random_genome(random.Random(4))
        r = simulate(g, "zone", random.Random(6), FAST_TABLE)
        self.assertIn(r.outcome, ("make2", "make3", "miss", "violation"))
        self.assertIn(r.pts, (0, 2, 3))
        self.assertGreater(len(r.events), 0)
        self.assertGreater(len(r.frames), 0)
        self.assertTrue(r.events[0].text.endswith("发起"))

    def test_batch_two_environments(self):
        import random
        g = tactics.random_genome(random.Random(7))
        stats = run_batch(g, random.Random(8), n_per_def=4, table=FAST_TABLE)
        self.assertAlmostEqual(stats["ppp"],
                               (stats["ppp_man"] + stats["ppp_zone"]) / 2)


class TestEvolution(unittest.TestCase):
    def test_best_monotone_nondecreasing(self):
        _champ, hist = evolve(pop_size=8, gens=4, seed=11, n_per_def=3,
                              log=lambda *_: None)
        bests = [h["best"] for h in hist]
        for a, b in zip(bests, bests[1:]):
            self.assertGreaterEqual(b + 1e-9, a,
                                    msg=f"精英保留失效: {bests}")

    def test_run_completes(self):
        champ, hist = evolve(pop_size=8, gens=3, seed=2, n_per_def=3,
                             log=lambda *_: None)
        self.assertIn(champ["ppp"], (hist[-1]["best"],))
        self.assertGreaterEqual(champ["ppp"], 0.0)


class TestCSI(unittest.TestCase):
    def test_report_sections(self):
        import random
        g = tactics.random_genome(random.Random(9))
        text, data = report(g, n=6, seed=5)
        self.assertIn("CSI", text)
        self.assertIn("为什么有效", text)
        self.assertIn("命中模型", text)
        self.assertGreater(data["n"], 0)
        self.assertIsNotNone(data["representative"])

    def test_region_names(self):
        self.assertEqual(region_name((0.0, 8.0)), "弧顶")
        self.assertEqual(region_name((-6.4, 2.5)), "左底角")
        self.assertEqual(region_name((0.5, 1.0)), "篮下")


if __name__ == "__main__":
    unittest.main()
