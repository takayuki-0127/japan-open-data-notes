"""1118 上限のある能力を上げ続けると、表に出る強さはどこで伸びなくなるのか？（架空のデータ）

作成者が置いた架空のゲームで、会心率（上限100%）を能力の点で上げていく。
会心率＝基本10%＋場面ごとの上乗せ（0%・30%・60%のどれか、確率50%・30%・20%）＋能力の点×1%。上限を超えた分は効かない。
会心すると2倍のダメージ（素のダメージ100）。能力の画面に出る会心率（基本＋点、上乗せなし）と、
戦いで効く会心率・1回の平均ダメージを比べ、1点あたりの伸びがどこから縮むかを、式（上乗せの出方で平均）と乱数の攻撃で数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1118
SRC = "架空のゲームの会心率（作成者が置いた上限と上乗せ、乱数の攻撃、seed 1118）"
BASE_RATE = 10.0
DMG = 100.0
CRIT_X = 2.0
P_MAX = 120
HITS = 20000

BUFFS = {
    "基本（0・30・60%を50・30・20%）": (np.array([0.0, 30.0, 60.0]), np.array([0.5, 0.3, 0.2])),
    "いつも21%": (np.array([21.0]), np.array([1.0])),
    "広い（0%か60%を65・35%）": (np.array([0.0, 60.0]), np.array([0.65, 0.35])),
    "0〜42%に一様": (np.arange(0.0, 43.0), np.full(43, 1 / 43)),
}
BASE_BUFF = "基本（0・30・60%を50・30・20%）"


def r(x, d=2):
    return round(float(x), d)


def eff_rate(p, buff, cap=100.0, base=BASE_RATE):
    """戦いで効く会心率の平均（%）：上乗せの出方で平均した式の値"""
    v, w = buff
    return float((np.minimum(base + v + p, cap) * w).sum())


def first_p(gains, kind):
    """kind="below1"：1点の伸びが1を下回る最初の点、"half"：0.5以下、"zero"：0"""
    if kind == "below1":
        idx = np.nonzero(gains < 1 - 1e-9)[0]
    elif kind == "half":
        idx = np.nonzero(gains <= 0.5 + 1e-9)[0]
    else:
        idx = np.nonzero(gains <= 1e-9)[0]
    return int(idx[0]) if len(idx) else None


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    buff = BUFFS[BASE_BUFF]
    mean_buff = float((buff[0] * buff[1]).sum())
    ps = np.arange(0, P_MAX + 1)

    # 1) 式の値：点ごとの効く会心率、1点あたりの伸び、平均の上乗せで見積もった値
    rows = []
    for p in ps:
        e = eff_rate(p, buff)
        naive = min(BASE_RATE + mean_buff + p, 100.0)
        rows.append({"points": int(p), "shown_rate": BASE_RATE + p, "effective_rate": r(e, 3), "naive_rate_mean_buff": r(naive, 3),
                     "mean_damage": r(DMG * (1 + (CRIT_X - 1) * e / 100), 3),
                     "share_over_cap": r(float((buff[1] * (BASE_RATE + buff[0] + p > 100)).sum()) * 100, 1)})
    curve = pd.DataFrame(rows)
    curve["gain_next_point"] = np.round(np.r_[np.diff(curve.effective_rate), np.nan], 3)
    gains = curve.gain_next_point.values[:-1]

    # 2) 乱数の攻撃（点を5きざみ、各20,000回）
    sim = []
    ex_rows = []
    for p in range(0, P_MAX + 1, 5):
        k = rng.choice(len(buff[0]), HITS, p=buff[1])
        rate = np.minimum(BASE_RATE + buff[0][k] + p, 100.0)
        crit = rng.random(HITS) * 100 < rate
        dmg = DMG * np.where(crit, CRIT_X, 1.0)
        sim.append({"points": p, "sim_mean_damage": r(dmg.mean(), 3), "sim_crit_share": r(crit.mean() * 100, 2),
                    "exact_mean_damage": float(curve.mean_damage[p])})
        if p in (0, 30, 60, 90):
            for i in range(500):
                ex_rows.append({"points": p, "hit": i + 1, "buff": float(buff[0][k[i]]), "rate": float(rate[i]),
                                "crit": int(crit[i]), "damage": float(dmg[i])})
    sim = pd.DataFrame(sim)
    sim["diff"] = np.round(sim.sim_mean_damage - sim.exact_mean_damage, 3)
    curve = curve.merge(sim, on="points", how="left")
    curve.to_csv(RES / "curve.csv", index=False)
    pd.DataFrame(ex_rows).to_csv(DATA / "example_hits.csv", index=False)

    p_shown_cap = int(100 - BASE_RATE)
    p_naive_stop = int(np.ceil(100 - BASE_RATE - mean_buff))
    key_p = {}
    for p in [0, 20, 30, 45, 60, 69, 75, 90, 100, 120]:
        row = curve.loc[curve.points == p].iloc[0]
        key_p[str(p)] = {"shown_rate": float(row.shown_rate), "effective_rate": float(row.effective_rate),
                         "naive_rate_mean_buff": float(row.naive_rate_mean_buff), "mean_damage": float(row.mean_damage),
                         "share_over_cap": float(row.share_over_cap),
                         "gain_next_point": None if np.isnan(row.gain_next_point) else float(row.gain_next_point)}
    eff0 = eff_rate(0, buff)
    # 表示が上限に届く90点までに入れた点のうち、効いた分
    added_at_shown_cap = eff_rate(p_shown_cap, buff) - eff0
    # 30点ずつの区間の1点あたりの伸び
    seg = {f"{a}-{b}": r((eff_rate(b, buff) - eff_rate(a, buff)) / (b - a), 3) for a, b in [(0, 30), (30, 60), (60, 90), (90, 120)]}

    # 3) 確かめ：上乗せの出方×上限×基本の会心率（16通り）
    grid = []
    for (bname, bf), cap, base in itertools.product(BUFFS.items(), [100.0, 75.0], [10.0, 25.0]):
        p_show = int(cap - base)
        pp = np.arange(0, p_show + 61)
        e = np.array([eff_rate(p, bf, cap, base) for p in pp])
        g = np.diff(e)
        mb = float((bf[0] * bf[1]).sum())
        grid.append({"buff": bname, "cap": cap, "base_rate": base,
                     "p_gain_below_1": first_p(g, "below1"), "p_gain_half_or_less": first_p(g, "half"), "p_gain_zero": first_p(g, "zero"),
                     "p_shown_reaches_cap": p_show,
                     "p_naive_stop_mean_buff": int(np.ceil(cap - base - mb)),
                     "start_over_shown_cap_point": r(first_p(g, "below1") / p_show, 3),
                     "half_over_shown_cap_point": r(first_p(g, "half") / p_show, 3),
                     "gain_at_naive_stop": r(g[int(np.ceil(cap - base - mb)) - 1], 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gvar = grid[grid.buff != "いつも21%"]

    out = {"base_rate": BASE_RATE, "crit_multiplier": CRIT_X, "base_damage": DMG, "cap": 100.0, "per_point": 1.0,
           "buff": {"values": buff[0].tolist(), "probs": buff[1].tolist(), "mean": r(mean_buff, 2)},
           "p_gain_starts_falling": first_p(gains, "below1"), "p_gain_half_or_less": first_p(gains, "half"), "p_gain_zero": first_p(gains, "zero"),
           "p_shown_reaches_cap": p_shown_cap, "p_naive_stop_mean_buff": p_naive_stop,
           "shown_rate_when_gain_starts_falling": BASE_RATE + first_p(gains, "below1"),
           "effective_rate_p0": r(eff0, 2),
           "added_effective_at_shown_cap": r(added_at_shown_cap, 2),
           "share_of_points_effective_at_shown_cap": r(added_at_shown_cap / p_shown_cap * 100, 1),
           "gain_per_point_by_segment": seg,
           "key_points": key_p,
           "sim_hits_per_level": HITS, "sim_max_abs_diff_damage": r(sim["diff"].abs().max(), 3),
           "grid_count": len(grid),
           "grid_start_over_shown_cap_range_varied_buff": [r(gvar.start_over_shown_cap_point.min(), 3), r(gvar.start_over_shown_cap_point.max(), 3)],
           "grid_half_over_shown_cap_range_varied_buff": [r(gvar.half_over_shown_cap_point.min(), 3), r(gvar.half_over_shown_cap_point.max(), 3)],
           "grid_start_points_range_varied_buff": [int(gvar.p_gain_below_1.min()), int(gvar.p_gain_below_1.max())],
           "grid_gain_at_naive_stop_range_varied_buff": [r(gvar.gain_at_naive_stop.min(), 3), r(gvar.gain_at_naive_stop.max(), 3)],
           "grid_const_buff_start_equals_naive": bool((grid[grid.buff == "いつも21%"].p_gain_below_1 ==
                                                       grid[grid.buff == "いつも21%"].p_naive_stop_mean_buff).all()),
           "grid_const_buff_start_over_shown_cap_range": [r(grid[grid.buff == "いつも21%"].start_over_shown_cap_point.min(), 3),
                                                          r(grid[grid.buff == "いつも21%"].start_over_shown_cap_point.max(), 3)]}
    json.dump(out, open(RES / "a1118_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：画面の会心率・効く会心率・平均の上乗せで見積もった会心率
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.plot(curve.points, np.minimum(curve.shown_rate, 130), color=GRAY, lw=1.5, ls="--", label="画面に出る会心率（基本＋点、上乗せなし）")
    ax.plot(curve.points, curve.naive_rate_mean_buff, color=GREEN, lw=1.5, ls="-.", label="平均の上乗せ21%で見積もった会心率")
    ax.plot(curve.points, curve.effective_rate, color=BLUE, lw=2.4, label="戦いで効く会心率（上乗せの出方で平均、式の値）")
    s5 = curve.dropna(subset=["sim_crit_share"])
    ax.plot(s5.points, s5.sim_crit_share, "o", color=ORANGE, ms=4, label="乱数の攻撃20,000回で会心した割合")
    for p, txt in [(30, "30点から伸びが縮む"), (60, "60点から1点0.5%に"), (90, "90点で止まる")]:
        ax.axvline(p, color=INK, lw=0.7, ls=":")
        ax.text(p + 1, 8 + (p // 30 - 1) * 9, txt, fontsize=8.5)
    ax.set_xlim(0, P_MAX); ax.set_ylim(0, 132)
    ax.set_xlabel("会心率に入れた能力の点"); ax.set_ylabel("会心率（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("画面の会心率は90点で上限に届くが、戦いで効く会心率の伸びは30点から縮みはじめる", x=0.01, y=1.02, ha="left", fontsize=12)
    save(fig, "a1118_curve.png", SRC)

    # 図2：1点あたりの伸び（30点ずつの区間）と、上限を超えた場面の割合
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    labs = list(seg.keys()); vals = list(seg.values())
    bars = axes[0].bar(range(4), vals, color=[BLUE, BLUE, LIGHT, GRAY])
    for bb, v in zip(bars, vals):
        axes[0].text(bb.get_x() + bb.get_width() / 2, v + 0.02, f"{v:.3f}%", ha="center", fontsize=9)
    axes[0].set_xticks(range(4)); axes[0].set_xticklabels([f"{l}点" for l in labs])
    axes[0].set_ylim(0, 1.2); axes[0].set_ylabel("1点あたりの効く会心率の伸び（%）")
    axes[0].set_title("1点あたりの伸び（区間の平均、式の値）", loc="left", fontsize=11)
    axes[1].plot(curve.points, curve.share_over_cap, color=ORANGE, lw=2)
    axes[1].set_ylim(0, 105); axes[1].set_xlim(0, P_MAX)
    axes[1].set_xlabel("会心率に入れた能力の点"); axes[1].set_ylabel("上限を超えている場面の割合（%）")
    axes[1].set_title("上乗せを足すと100%を超える場面の割合", loc="left", fontsize=11)
    fig.suptitle("1点の伸びは 1 → 0.8 → 0.5 → 0 と段で縮む（上乗せ60%・30%の場面から順に上限を超えるため）", x=0.01, y=1.04, ha="left", fontsize=12)
    save(fig, "a1118_gain.png", SRC)

    # 図3：確かめ（16通り）。伸びが縮みはじめる点÷画面が上限に届く点
    fig, ax = plt.subplots(figsize=(13, 4.6))
    labels = []; v1 = []; v2 = []
    for _, g in grid.iterrows():
        short = {"0〜42%に一様": "一様\n0〜42%"}.get(g.buff, g.buff.split("（")[0] + ("\n0/30/60%" if g.buff.startswith("基本") else "\n0/60%" if g.buff.startswith("広い") else "\n21%"))
        if g.buff == "いつも21%":
            short = "いつも\n21%"
        labels.append(f"{short}\n上限{int(g.cap)}%\n基本{int(g.base_rate)}%")
        v1.append(g.start_over_shown_cap_point); v2.append(g.half_over_shown_cap_point)
    x = np.arange(len(grid))
    ax.bar(x - 0.2, v1, 0.4, color=BLUE, label="1点の伸びが縮みはじめる点 ÷ 画面が上限に届く点")
    ax.bar(x + 0.2, v2, 0.4, color=LIGHT, label="1点の伸びが半分以下になる点 ÷ 画面が上限に届く点")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylim(0, 1.2); ax.axhline(1, color=INK, lw=0.6, ls=":")
    ax.set_ylabel("画面が上限に届く点を1とした位置")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    fig.suptitle("確かめ（16通り）：上乗せが散らばるほど、伸びは画面の上限よりずっと手前で縮みはじめる", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1118_robust.png", SRC)

    print(curve.iloc[::5].to_string())
    print(grid.to_string())
    print({k: v for k, v in out.items() if k not in ("key_points",)})
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
