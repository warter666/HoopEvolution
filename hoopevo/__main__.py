"""CLI 入口：python -m hoopevo evolve | show | replay"""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        prog="hoopevo", description="HoopEvolution — 进化篮球战术 + CSI 解剖")
    sub = ap.add_subparsers(dest="cmd")

    ep = sub.add_parser("evolve", help="运行进化并打印每代日志 + 冠军 CSI 报告")
    ep.add_argument("--gens", type=int, default=12)
    ep.add_argument("--pop", type=int, default=24)
    ep.add_argument("--seed", type=int, default=0)
    ep.add_argument("--sims", type=int, default=8, help="每种防守的评估回合数")

    sp = sub.add_parser("show", help="快速进化并输出冠军的 CSI 解剖报告")
    sp.add_argument("--seed", type=int, default=0)

    rp = sub.add_parser("replay", help="进化冠军战术并打开 tkinter 回放")
    rp.add_argument("--seed", type=int, default=0)

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1

    from hoopevo.csi import report
    from hoopevo.evolution import evolve

    if args.cmd == "evolve":
        champ, _hist = evolve(pop_size=args.pop, gens=args.gens,
                              seed=args.seed, n_per_def=args.sims)
        print()
        text, _ = report(champ["genome"])
        print(text)
        return 0

    if args.cmd == "show":
        champ, hist = evolve(pop_size=12, gens=6, seed=args.seed, n_per_def=6)
        print()
        print("进化曲线:", " → ".join(f"{h['best']:.2f}" for h in hist))
        print()
        text, _ = report(champ["genome"])
        print(text)
        return 0

    if args.cmd == "replay":
        champ, hist = evolve(pop_size=12, gens=6, seed=args.seed, n_per_def=6)
        text, data = report(champ["genome"])
        print(text)
        if data["representative"] is not None:
            try:
                from hoopevo.replay_gui import replay
                replay(data["representative"],
                       title=f"TACTIC #{champ['genome'].tid:04d}")
            except Exception as e:
                print(f"回放不可用（{e}）")
        return 0


if __name__ == "__main__":
    sys.exit(main())
