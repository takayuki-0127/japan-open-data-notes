"""1113 攻撃力を10%上げるのと会心率を10ポイント上げるのでは、与えるダメージはどちらが伸びるのか？（架空のデータ）

作成者が置いた架空のゲームの数値。1回のダメージ＝攻撃力×（0.9〜1.1の一様な振れ）×（会心なら会心の倍率）。
基本は攻撃力1,000・会心率20%・会心の倍率1.5倍。
(1) 攻撃力+10%（1,100）と会心率+10ポイント（30%）の1回あたりの平均の伸びを、式と乱数100万回で数える
(2) よく見る数字（1回のダメージの真ん中）の伸びを数える
(3) 試し打ちの回数ごとに、合計ダメージで比べて本当に伸びる方を選べた割合を数える
(4) 確かめ：もとの会心率（0〜90%）×会心の倍率（1.5〜3倍）の40通りで、どちらが伸びるかを式で出す
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK

SEED = 1113
SRC = "架空のゲームの数値（作成者が置いた攻撃力・会心率・会心の倍率からの乱数、seed 1113）"
ATK, CRIT, MULT = 1000.0, 0.20, 1.5
LO, HI = 0.9, 1.1
N_HITS = 1_000_000
TRIAL_N = [10, 30, 100, 300, 1000]
TRIAL_REPS = 10000
MULTS = [1.5, 2.0, 2.5, 3.0]
CRITS = [round(0.1 * i, 1) for i in range(10)]


def r(x, d=4):
    return round(float(x), d)


def pct(x):
    return round(float(x) * 100, 2)


def gain_crit(c, m, add=0.10):
    """会心率を add 上げたときの1回あたりの平均の伸び（式）"""
    return (1 + (c + add) * (m - 1)) / (1 + c * (m - 1)) - 1


def hits(rng, n, atk, crit, mult):
    base = atk * rng.uniform(LO, HI, n)
    is_crit = rng.random(n) < crit
    return np.where(is_crit, base * mult, base), is_crit


def trial_totals(rng, n, reps, atk, crit, mult):
    """n 回打った合計を reps 組（1,000組ずつまとめて引く）"""
    tot = []
    for s in range(0, reps, 1000):
        k = min(1000, reps - s)
        u = rng.uniform(LO, HI, (k, n))
        c = rng.random((k, n)) < crit
        tot.append(atk * np.where(c, u * mult, u).sum(1))
    return np.concatenate(tot)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"attack": ATK, "crit_rate": CRIT, "crit_mult": MULT, "spread": [LO, HI],
                       "hits": N_HITS, "trial_reps": TRIAL_REPS}}

    # (1)(2) 3つの組み立て
    builds = {"もと": (ATK, CRIT), "攻撃力+10%": (ATK * 1.1, CRIT), "会心率+10ポイント": (ATK, CRIT + 0.10)}
    rows, one = [], []
    for name, (a, c) in builds.items():
        d, ic = hits(rng, N_HITS, a, c, MULT)
        formula = a * (1 + c * (MULT - 1))
        rows.append({"build": name, "attack": a, "crit_rate_pct": pct(c),
                     "mean_formula": r(formula, 2), "mean_sim": r(d.mean(), 2),
                     "median_sim": r(np.median(d), 2), "p10_sim": r(np.quantile(d, 0.1), 2),
                     "p90_sim": r(np.quantile(d, 0.9), 2), "crit_share_sim_pct": pct(ic.mean()),
                     "max_sim": r(d.max(), 2)})
        one.append(pd.DataFrame({"build": name, "hit": np.arange(1, 1001), "damage": np.round(d[:1000], 1),
                                 "crit": ic[:1000].astype(int)}))
    b = pd.DataFrame(rows)
    m0, med0 = b.loc[0, "mean_formula"], b.loc[0, "median_sim"]
    b["mean_gain_formula_pct"] = [pct(x / m0 - 1) for x in b["mean_formula"]]
    b["mean_gain_sim_pct"] = [pct(x / b.loc[0, "mean_sim"] - 1) for x in b["mean_sim"]]
    b["median_gain_sim_pct"] = [pct(x / med0 - 1) for x in b["median_sim"]]
    b.to_csv(RES / "builds.csv", index=False)
    pd.concat(one).to_csv(DATA / "hits_one_draw.csv", index=False)
    out["builds"] = b.to_dict("records")
    # 真ん中の式：会心でない回が半分を超えるとき、真ん中は会心でない回の (0.5/(1-c)) の位置
    out["median_formula"] = {name: r(a * (LO + (HI - LO) * 0.5 / (1 - c)), 2) for name, (a, c) in builds.items()}

    # (3) 試し打ちで選べた割合（倍率1.5・2.0・2.5）
    tr = []
    for m in [1.5, 2.0, 2.5]:
        g_atk, g_cr = 0.10, gain_crit(CRIT, m)
        better = "攻撃力+10%" if g_atk > g_cr else "会心率+10ポイント"
        for n in TRIAL_N:
            ta = trial_totals(rng, n, TRIAL_REPS, ATK * 1.1, CRIT, m)
            tc = trial_totals(rng, n, TRIAL_REPS, ATK, CRIT + 0.10, m)
            right = (ta > tc).mean() if better == "攻撃力+10%" else (tc > ta).mean()
            tr.append({"crit_mult": m, "crit_gain_formula_pct": pct(g_cr), "better_by_formula": better,
                       "trial_hits": n, "picked_better_pct": pct(right),
                       "atk_total_mean": r(ta.mean() / n, 2), "crit_total_mean": r(tc.mean() / n, 2)})
    tr = pd.DataFrame(tr)
    tr.to_csv(RES / "trial_pick.csv", index=False)
    out["trial_pick"] = tr.to_dict("records")

    # (4) 確かめ：40通り（式）
    gr = []
    for m in MULTS:
        for c in CRITS:
            g = gain_crit(c, m)
            gr.append({"crit_mult": m, "base_crit_pct": pct(c), "crit_gain_formula_pct": pct(g),
                       "attack_gain_pct": 10.0,
                       "winner": "会心率" if g > 0.10 + 1e-12 else ("同じ" if abs(g - 0.10) < 1e-12 else "攻撃力")})
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {
        "n": len(gr), "crit_wins": int((gr.winner == "会心率").sum()), "attack_wins": int((gr.winner == "攻撃力").sum()),
        "tie": int((gr.winner == "同じ").sum()),
        "crit_gain_range_pct": [float(gr.crit_gain_formula_pct.min()), float(gr.crit_gain_formula_pct.max())],
        "tie_mult_by_base_crit": {str(pct(c)): r(1 + 1 / (1 - c), 4) for c in CRITS},
        "by_mult": {str(m): {"crit_wins": int(((gr.crit_mult == m) & (gr.winner == "会心率")).sum()),
                             "attack_wins": int(((gr.crit_mult == m) & (gr.winner == "攻撃力")).sum()),
                             "tie": int(((gr.crit_mult == m) & (gr.winner == "同じ")).sum())} for m in MULTS},
    }

    # 図1：3つの倍率での平均の伸び（式）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    xs = np.arange(3)
    ms = [1.5, 2.0, 2.5]
    ga = [10.0] * 3
    gc = [pct(gain_crit(CRIT, m)) for m in ms]
    ax.bar(xs - 0.18, ga, 0.36, color=BLUE, label="攻撃力+10%")
    ax.bar(xs + 0.18, gc, 0.36, color=ORANGE, label="会心率+10ポイント")
    for x, v in zip(xs, ga):
        ax.text(x - 0.18, v + 0.2, f"{v}%", ha="center", fontsize=9)
    for x, v in zip(xs, gc):
        ax.text(x + 0.18, v + 0.2, f"{v}%", ha="center", fontsize=9)
    ax.set_xticks(xs, [f"会心の倍率{m}倍" for m in ms])
    ax.set_ylim(0, 14)
    ax.set_ylabel("1回あたりの平均ダメージの伸び（%）")
    ax.set_title("もとの会心率20%で、平均の伸び（式どおり）")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1113_mean_gain.png", SRC)

    # 図2：試し打ちの回数と、伸びる方を選べた割合
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for m, col in zip([1.5, 2.0, 2.5], [BLUE, GRAY, ORANGE]):
        s = tr[tr.crit_mult == m]
        ax.plot(s.trial_hits, s.picked_better_pct, marker="o", color=col,
                label=f"会心{m}倍（伸びる方：{s.better_by_formula.iloc[0]}）")
    ax.axhline(50, color=GRAY, lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_xticks(TRIAL_N, [str(n) for n in TRIAL_N])
    ax.set_ylim(0, 100)
    ax.set_xlabel("それぞれの組み立てで試し打ちした回数")
    ax.set_ylabel("合計で比べて伸びる方を選べた割合（%）")
    ax.set_title("試し打ちの合計で比べたとき")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    save(fig, "a1113_trial_pick.png", SRC)

    # 図3：もとの会心率と会心率+10ポイントの伸び（式）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for m, col in zip(MULTS, [BLUE, GRAY, ORANGE, INK]):
        s = gr[gr.crit_mult == m]
        ax.plot(s.base_crit_pct, s.crit_gain_formula_pct, marker="o", ms=4, color=col, label=f"会心{m}倍")
    ax.axhline(10, color=BLUE, lw=1.2, ls="--")
    ax.text(91, 10.4, "攻撃力+10%", color=BLUE, fontsize=9, ha="right")
    ax.set_ylim(0, max(gr.crit_gain_formula_pct) * 1.1)
    ax.set_xlabel("もとの会心率（%）")
    ax.set_ylabel("会心率+10ポイントでの伸び（%）")
    ax.set_title("会心率+10ポイントの伸び（式どおり、40通り）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1113_grid.png", SRC)

    (RES / "a1113_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
