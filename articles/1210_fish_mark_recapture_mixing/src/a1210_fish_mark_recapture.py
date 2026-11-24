"""1210 印を付けて放した魚が何匹また捕まったかで、池の魚の数はどこまで分かるのか？（架空のデータ）

架空の池（A池）を5つの区域に分け、本当の魚の数（2,000匹）と、魚が区域のあいだを動く速さを作成者が置く。
1日目に岸ぞいの区域1で200匹を捕まえて印を付けて放し、何日か後にもう一度200匹を捕まえて、印のある魚の数から全体を見込む。
2回目を同じ岸だけで捕るか、5つの区域に分けて捕るか、待つ日数、印のある魚が減る割合（印が取れる・弱って死ぬ）を変えて、
見込みのずれと幅を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1210
SRC = "架空の池の魚（作成者が乱数で作成、seed 1210）"
N, Z, M, C = 2000, 5, 200, 200
DAYS = [1, 2, 3, 5, 7, 10, 14, 21, 30]
W_EQUAL = np.ones(Z)
W_UNEVEN = np.array([2.0, 1.0, 1.0, 0.5, 0.5])   # 岸ぞいの区域1に魚が多い置き方


def est(R):
    return (M + 1) * (C + 1) / (R + 1) - 1


def run(rng, reps, m, q, w, days=DAYS):
    w = w / w.sum()
    zone = rng.choice(Z, p=w, size=(reps, N)).astype(np.int8)
    u = rng.random((reps, N))
    u[zone != 0] = 2.0
    idx = np.argpartition(u, M, axis=1)[:, :M]
    marked = np.zeros((reps, N), bool)
    np.put_along_axis(marked, idx, True, axis=1)
    out = {}
    for d in range(1, max(days) + 1):
        mv = rng.random((reps, N)) < m
        newz = rng.choice(Z, p=w, size=(reps, N)).astype(np.int8)
        zone = np.where(mv, newz, zone)
        if q > 0:
            marked &= rng.random((reps, N)) >= q
        if d in days:
            n = np.stack([(zone == z).sum(1) for z in range(Z)], 1)
            k = np.stack([((zone == z) & marked).sum(1) for z in range(Z)], 1)
            # A：2回目も岸ぞいの区域1だけで200匹
            RA = rng.hypergeometric(k[:, 0], n[:, 0] - k[:, 0], C)
            # B：5つの区域で40匹ずつ
            RB = rng.hypergeometric(k, n - k, C // Z).sum(1)
            out[d] = dict(A=est(RA), B=est(RB), RA=RA, RB=RB, share_zone1=k[:, 0] / np.maximum(k.sum(1), 1),
                          left=k.sum(1))
    return out


def pct(x):
    return round(float(x), 2)


def summarize(o, d, key):
    e = o[d][key]
    b = (e / N - 1) * 100
    return dict(mean_est=round(float(e.mean()), 1), median_est=round(float(np.median(e)), 1),
                bias_mean_pct=pct(b.mean()), bias_median_pct=pct(np.median(b)),
                q05_pct=pct(np.quantile(b, .05)), q95_pct=pct(np.quantile(b, .95)),
                within20_pct=pct((np.abs(b) <= 20).mean() * 100),
                recaught_mean=round(float(o[d]["R" + key].mean()), 2))


def main():
    rng = np.random.default_rng(SEED)
    base = dict(m=0.1, q=0.005)
    o = run(rng, 2000, base["m"], base["q"], W_EQUAL)
    rows = []
    for d in DAYS:
        for key, lab in [("A", "same_shore"), ("B", "five_zones")]:
            s = summarize(o, d, key)
            rows.append(dict(day=d, design=lab, **s,
                             marked_share_in_zone1_pct=pct(o[d]["share_zone1"].mean() * 100),
                             marked_left_mean=round(float(o[d]["left"].mean()), 1)))
    days_tab = pd.DataFrame(rows)
    days_tab.to_csv(RES / "base_by_day.csv", index=False)

    # 理想（印が減らない・5つの区域）での幅
    o0 = run(rng, 2000, base["m"], 0.0, W_EQUAL, days=[10])
    ideal = summarize(o0, 10, "B")

    # 例の1回（基本・10日目）
    ex_rows = []
    for d in DAYS:
        ex_rows.append(dict(day=d, recaught_same_shore=int(o[d]["RA"][0]), est_same_shore=round(float(o[d]["A"][0]), 1),
                            recaught_five_zones=int(o[d]["RB"][0]), est_five_zones=round(float(o[d]["B"][0]), 1),
                            marked_left=int(o[d]["left"][0])))
    pd.DataFrame(ex_rows).to_csv(DATA / "example_pond.csv", index=False)

    # 確かめ：動く速さ × 印の減り × 魚の多い区域の有無（18通り、各500回）
    rows = []
    for m in [0.03, 0.1, 0.3]:
        for q in [0.0, 0.005, 0.02]:
            for wname, w in [("同じ", W_EQUAL), ("岸ぞいに多い", W_UNEVEN)]:
                og = run(rng, 300, m, q, w)
                for d in DAYS:
                    for key, lab in [("A", "same_shore"), ("B", "five_zones")]:
                        s = summarize(og, d, key)
                        rows.append(dict(move_per_day=m, mark_loss_per_day=q, density=wname, day=d, design=lab,
                                         bias_mean_pct=s["bias_mean_pct"], bias_median_pct=s["bias_median_pct"],
                                         q05_pct=s["q05_pct"], q95_pct=s["q95_pct"], within20_pct=s["within20_pct"]))
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # まとめ
    def best_day(sub):
        sub = sub.assign(absb=sub.bias_mean_pct.abs())
        r = sub.sort_values(["absb", "day"]).iloc[0]
        return int(r.day), float(r.bias_mean_pct)

    combos = []
    for (m, q, dn, des), sub in grid.groupby(["move_per_day", "mark_loss_per_day", "density", "design"]):
        bd, bb = best_day(sub)
        combos.append(dict(move_per_day=m, mark_loss_per_day=q, density=dn, design=des, best_day=bd,
                           best_bias_mean_pct=bb,
                           day1_bias_mean_pct=float(sub[sub.day == 1].bias_mean_pct.iloc[0]),
                           day30_bias_mean_pct=float(sub[sub.day == 30].bias_mean_pct.iloc[0])))
    combos = pd.DataFrame(combos)
    combos.to_csv(RES / "grid_best_day.csv", index=False)

    bt = days_tab.set_index(["day", "design"])
    g_eq_B_q0 = grid[(grid.density == "同じ") & (grid.design == "five_zones") & (grid.mark_loss_per_day == 0)]
    g_un_B = grid[(grid.density == "岸ぞいに多い") & (grid.design == "five_zones") & (grid.mark_loss_per_day == 0)]
    g_A_day1 = grid[(grid.design == "same_shore") & (grid.day == 1)]
    out = dict(
        setting=dict(N=N, zones=Z, marked=M, second_catch=C, move_per_day=base["m"], mark_loss_per_day=base["q"]),
        base_day=dict(
            same_shore_day1=bt.loc[(1, "same_shore")].to_dict(), same_shore_day10=bt.loc[(10, "same_shore")].to_dict(),
            same_shore_day30=bt.loc[(30, "same_shore")].to_dict(),
            five_zones_day1=bt.loc[(1, "five_zones")].to_dict(), five_zones_day10=bt.loc[(10, "five_zones")].to_dict(),
            five_zones_day30=bt.loc[(30, "five_zones")].to_dict()),
        mark_left_formula_day30_pct=pct((1 - base["q"]) ** 30 * 100),
        overestimate_formula_day30_pct=pct((1 / (1 - base["q"]) ** 30 - 1) * 100),
        ideal_five_zones_no_loss_day10=ideal,
        grid_summary=dict(
            all_bias_mean_range=[float(grid.bias_mean_pct.min()), float(grid.bias_mean_pct.max())],
            five_zones_equal_day1_bias_mean_range=[
                float(grid[(grid.density == "同じ") & (grid.design == "five_zones") & (grid.day == 1)].bias_mean_pct.min()),
                float(grid[(grid.density == "同じ") & (grid.design == "five_zones") & (grid.day == 1)].bias_mean_pct.max())],
            same_shore_day1_bias_mean_range=[float(g_A_day1.bias_mean_pct.min()), float(g_A_day1.bias_mean_pct.max())],
            five_zones_equal_noloss_bias_mean_range=[float(g_eq_B_q0.bias_mean_pct.min()),
                                                       float(g_eq_B_q0.bias_mean_pct.max())],
            five_zones_uneven_noloss_day1_bias_mean_range=[
                float(g_un_B[g_un_B.day == 1].bias_mean_pct.min()), float(g_un_B[g_un_B.day == 1].bias_mean_pct.max())],
            five_zones_uneven_noloss_day30_bias_mean_range=[
                float(g_un_B[g_un_B.day == 30].bias_mean_pct.min()), float(g_un_B[g_un_B.day == 30].bias_mean_pct.max())],
            same_shore_best_day_range=[int(combos[combos.design == "same_shore"].best_day.min()),
                                       int(combos[combos.design == "same_shore"].best_day.max())],
            day30_bias_mean_by_loss={str(q): [float(grid[(grid.day == 30) & (grid.mark_loss_per_day == q)].bias_mean_pct.min()),
                                                float(grid[(grid.day == 30) & (grid.mark_loss_per_day == q)].bias_mean_pct.max())]
                                       for q in [0.0, 0.005, 0.02]},
        ),
    )
    json.dump(out, open(RES / "a1210_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：待つ日数と見込みのずれ（基本）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for lab, key, col in [("2回目も同じ岸（区域1）だけで捕る", "same_shore", BLUE), ("2回目は5つの区域で40匹ずつ", "five_zones", ORANGE)]:
        s = days_tab[days_tab.design == key]
        ax.plot(s.day, s.bias_mean_pct, marker="o", color=col, label=lab + "（平均）")
        ax.fill_between(s.day, s.q05_pct, s.q95_pct, color=col, alpha=0.15)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xlabel("印を付けてから2回目に捕るまでの日数"); ax.set_ylabel("本当の数（2,000匹）とのずれ（%）\n帯は5〜95%", linespacing=1.6)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("同じ岸で捕ると、待つ日数が短いほど少なく見込んだ\n（魚が1日に動く割合0.1、印のある魚が1日に減る割合0.5%）")
    save(fig, "a1210_days.png", SRC)

    # 図2：印のある魚のうち区域1にいる割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    s = days_tab[days_tab.design == "same_shore"]
    ax.plot(s.day, s.marked_share_in_zone1_pct, marker="o", color=BLUE)
    ax.axhline(20, color=GRAY, ls="--", lw=1)
    ax.text(30, 14, "池全体に混ざったときの20%", ha="right", fontsize=8.5, color=GRAY)
    ax.set_ylim(0, 100); ax.set_xlabel("印を付けてからの日数"); ax.set_ylabel("印のある魚のうち、\n区域1にいる割合（%）", linespacing=1.6)
    ax.set_title("印のある魚は、放した岸に長く残った（魚が1日に動く割合0.1）")
    save(fig, "a1210_mixing.png", SRC)

    # 図3：18通りでの、1日目と30日目のずれ（中央値）
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.2), sharey=True)
    for a, des, tt in [(axs[0], "same_shore", "同じ岸だけで捕る"), (axs[1], "five_zones", "5つの区域で40匹ずつ")]:
        sub = combos[combos.design == des].reset_index(drop=True)
        xx = np.arange(len(sub))
        a.bar(xx - 0.2, sub.day1_bias_mean_pct, width=0.4, color=LIGHT, label="1日後")
        a.bar(xx + 0.2, sub.day30_bias_mean_pct, width=0.4, color=BLUE if des == "same_shore" else ORANGE,
              label="30日後")
        a.axhline(0, color=INK, lw=0.8); a.set_xticks([])
        a.set_title(tt, fontsize=11)
        a.set_xlabel("置き方の18通り\n（動く速さ × 印の減り × 魚の多い区域）", fontsize=9)
        a.legend(frameon=False, fontsize=8, loc="upper left" if des == "same_shore" else "lower left")
    axs[0].set_ylabel("見込みのずれ（%、平均）")
    fig.suptitle("見込みのずれは、捕り方・待つ日数・印の減りで向きが変わった（各300回）", fontsize=12, y=1.03)
    save(fig, "a1210_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(days_tab.to_string())


if __name__ == "__main__":
    main()
