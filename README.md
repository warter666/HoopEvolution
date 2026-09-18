# 🧬 HoopEvolution — 进化篮球战术 + CSI 解剖

> 篮球项目栈的研究型顶点：**让 AI 在自建的篮球世界里进化战术，并用 CSI 说清楚"为什么有效"。**
> 策划书见 [docs/DESIGN.md](docs/DESIGN.md)；设计输入见上级 [BASKETBALL_LESSONS.md](../BASKETBALL_LESSONS.md)。

```text
   进化引擎（战术基因组）          ┌────────────────────────┐
        │ Generate                │ 🕵️ CSI 解剖报告          │
        ▼                         │ · 为什么有效（数据驱动）  │
   回合模拟器（5v5）               │ · 代表性回合时间线       │
   人盯人 + 联防 双环境            │ · tkinter 可回放复核     │
        │ Fitness = ppp           └────────────────────────┘
        └── Select / Mutate / Crossover ⟲
```

## 快速开始

```bash
cd HoopEvolution

python -m hoopevo evolve --gens 12 --pop 24    # 完整进化 + 冠军 CSI 报告
python -m hoopevo show                          # 快速进化 + 解剖报告
python -m hoopevo replay                        # 进化冠军 + tkinter 回放动画

python -m unittest discover -s tests            # 13 个测试
```

## 它在做什么

1. **物理标定命中模型**：启动时用 `BasketballPhysics` 的 shotlab 引擎对 6 个距离
   锚点各跑 120 次蒙特卡洛 → "空位命中率-距离"曲线（shotlab 缺席时退化文献表并声明）。
2. **战术 = 基因组**：5 名球员各 2 个路标点 + 终结者 + 出手时机。变异=路标抖动/
   换射手/换路线，交叉=按球员混血。
3. **双防守环境评估**：人盯人（贪心指派 + 反应延迟 0.25s = 空位的来源）与
   联防（哨位随球滑动）。fitness = 两种防守的平均每回合得分（ppp）。
4. **可解释的涌现**：无球人贴近射手的防守人 0.6m → 掩护成立，防守人被延缓 0.8s
   ——进化找到的每个战术优势都能被 CSI 用事件流讲出来。

## 一份真实的 CSI 输出

```text
样本 24 回合 · 命中率 54% · ppp 1.62 · 人盯人 1.25 / 联防 2.00
为什么有效：
• 射手终结点: 弧顶 24（平均出手 9.1 m，平均防守距离 2.41 m）
• 掩护 1.5 次/回合（被延缓的防守人给射手制造出手空间）
• 平均传球 2.0 次 → 防守总位移 49.0 m/回合（消耗）
代表性回合：
  t= 0.9  C 掩护成立：PF 的防守人被延缓 0.8s
  t= 5.2  传球 SG → PF（终结输送）
  t= 5.5  PF 弧顶出手 9.1 m · 最近防守 0.9 m · 命中概率 0.41 ✓ 命中
```

## 已知局限（= M2 方向）

* 联防偏弱（外线 factor 顶满），冠军会专打联防外线——真实但不平衡，
  M2 让**防守也进化**（攻防军备竞赛）。
* 命中曲线锚点 120 样本有 ±5% 抽样噪声；M2 提高样本量并做双种子平均。
* 进化结果暂只输出到 stdout（文件持久化待白名单目录方案）。

## 项目结构

```text
HoopEvolution/
├── hoopevo/
│   ├── court.py       # 半场几何 / 区域命名
│   ├── shot_model.py  # 物理标定命中模型（shotlab 复用 + 回退）
│   ├── tactics.py     # 战术基因组 + 遗传算子
│   ├── simulate.py    # 5v5 回合模拟器（事件流 + 回放帧）
│   ├── evolution.py   # GA：精英保留 / 锦标赛 / 固定 tid 可复现评估
│   ├── csi.py         # 🕵️ 解剖报告
│   ├── replay_gui.py  # tkinter 回放动画
│   └── __main__.py    # evolve / show / replay
├── tests/             # 13 个测试（精英单调性 / 模拟确定性 / CSI 结构）
└── docs/DESIGN.md     # 策划书
```

## License

MIT
