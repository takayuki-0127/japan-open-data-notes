"""1186 平均の対応時間が短い担当は、手早い担当なのか、易しい問い合わせを受けた担当なのか？（架空のデータ）

作成者が置いた架空の会社の問い合わせ窓口。担当20人（担当01〜20）が1か月に1人300件ずつ受ける。
問い合わせの種類は4つ（易しい順にA・B・C・D、1件の時間の中央値は6・12・25・50分）。
担当ごとの本当の手早さ（同じ問い合わせにかかる時間の倍率）を作成者が置く。
担当ごとに受ける種類の混ざり方が違う（易しい混ざり方と難しい混ざり方の間のどこか）。
基本では、手早い担当ほど難しい種類を多く受ける（手早さと難しい種類の受けやすさの相関0.5）。
(1) 平均の対応時間の順と、種類をそろえた比（実際の時間の合計÷種類ごとの全体の平均で見込んだ時間の合計）の順を、
    本当の手早さの順と比べる（200回の平均）
(2) 確かめ：手早さと混ざり方の相関4通り×混ざり方の差3通り×種類の中の見えない難しさの偏り3通りの36通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1186
SRC = "架空の会社の問い合わせ窓口（作成者が置いた種類・時間・担当の手早さからの乱数、seed 1186）"
N_AGENT, N_CASE = 20, 300
TYPES = ["A", "B", "C", "D"]
MED_MIN = np.array([6.0, 12.0, 25.0, 50.0])
EASY_MIX = np.array([0.6, 0.3, 0.08, 0.02])
HARD_MIX = np.array([0.1, 0.25, 0.35, 0.3])
SPEED_SD = 0.12      # 手早さ（対数）の標準偏差
CASE_SD = 0.5        # 1件の時間の散らばり（対数）
HIDDEN_SD = 0.3      # 種類の中の見えない難しさ（対数）。CASE_SD の一部
BASE = {"rho": 0.5, "spread": "広い", "gamma": 0.0}
SPREADS = {"同じ": (0.5, 0.5), "狭い": (0.35, 0.65), "広い": (0.0, 1.0)}
RHOS = [-0.5, 0.0, 0.5, 0.8]
GAMMAS = [0.0, 0.15, 0.3]
R_BASE, R_GRID = 200, 200
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def phi(z):
    from math import erf, sqrt
    return 0.5 * (1 + np.vectorize(erf)(z / sqrt(2)))


def ranks(x):
    o = np.argsort(x, kind="stable")
    rk = np.empty(len(x))
    rk[o] = np.arange(len(x))
    return rk


def rank_corr(a, b):
    ra, rb = ranks(a), ranks(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def one_month(rng, rho, spread, gamma):
    """1か月分。返り値：担当ごとの本当の倍率・難しい種類の割合・平均時間・種類をそろえた比、と1件ずつの表"""
    lo, hi = SPREADS[spread]
    z_speed = rng.standard_normal(N_AGENT)
    speed = np.exp(SPEED_SD * z_speed)               # 小さいほど手早い
    z_mix = -rho * z_speed + np.sqrt(1 - rho ** 2) * rng.standard_normal(N_AGENT)  # 手早い（z_speed が小さい）ほど難しい種類
    h = lo + (hi - lo) * phi(z_mix)
    agent = np.repeat(np.arange(N_AGENT), N_CASE)
    mix = (1 - h)[:, None] * EASY_MIX + h[:, None] * HARD_MIX
    u = rng.random(len(agent))
    typ = (u[:, None] > np.cumsum(mix[agent], axis=1)).sum(axis=1)
    typ = np.minimum(typ, len(TYPES) - 1)
    hidden = HIDDEN_SD * rng.standard_normal(len(agent)) + gamma * (h[agent] - 0.5) * 2
    noise = np.sqrt(CASE_SD ** 2 - HIDDEN_SD ** 2) * rng.standard_normal(len(agent))
    t = MED_MIN[typ] * speed[agent] * np.exp(hidden + noise)
    type_mean = np.array([t[typ == k].mean() for k in range(len(TYPES))])
    expect = type_mean[typ]
    avg = np.bincount(agent, t) / N_CASE
    adj = np.bincount(agent, t) / np.bincount(agent, expect)
    hard = np.bincount(agent, typ >= 2) / N_CASE
    return speed, h, hard, avg, adj, agent, typ, t


def summarize(rng, rho, spread, gamma, R):
    c_raw, c_adj, top_raw, top_adj, fastest_true_rank, fastest_hard = [], [], [], [], [], []
    for _ in range(R):
        speed, h, hard, avg, adj, *_ = one_month(rng, rho, spread, gamma)
        c_raw.append(rank_corr(avg, speed))
        c_adj.append(rank_corr(adj, speed))
        true5 = set(np.argsort(speed)[:5])
        top_raw.append(len(true5 & set(np.argsort(avg)[:5])))
        top_adj.append(len(true5 & set(np.argsort(adj)[:5])))
        f = int(np.argmin(avg))
        fastest_true_rank.append(int(ranks(speed)[f]) + 1)
        fastest_hard.append(hard[f])
    return {"rankcorr_raw": r(np.mean(c_raw), 3), "rankcorr_adj": r(np.mean(c_adj), 3),
            "top5_hit_raw": r(np.mean(top_raw), 2), "top5_hit_adj": r(np.mean(top_adj), 2),
            "raw_fastest_true_rank_median": r(np.median(fastest_true_rank), 1),
            "raw_fastest_in_true_top5_pct": r(np.mean(np.array(fastest_true_rank) <= 5) * 100, 1),
            "raw_fastest_hard_share_mean_pct": r(np.mean(fastest_hard) * 100, 1),
            "rankcorr_raw_neg_pct": r(np.mean(np.array(c_raw) < 0) * 100, 1)}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"agents": N_AGENT, "cases_per_agent": N_CASE, "types": TYPES, "median_min": MED_MIN.tolist(),
                       "easy_mix": EASY_MIX.tolist(), "hard_mix": HARD_MIX.tolist(), "speed_sd_log": SPEED_SD,
                       "case_sd_log": CASE_SD, "hidden_sd_log": HIDDEN_SD, **BASE, "reps": R_BASE,
                       "spreads": {k: list(v) for k, v in SPREADS.items()},
                       "gamma_time_factor_hardest_mix": {str(g): r(np.exp(g), 3) for g in GAMMAS},
                       "gamma_time_factor_easiest_mix": {str(g): r(np.exp(-g), 3) for g in GAMMAS}}}

    # 例：1か月分
    speed, h, hard, avg, adj, agent, typ, t = one_month(rng, BASE["rho"], BASE["spread"], BASE["gamma"])
    ex = pd.DataFrame({"agent": [f"担当{i + 1:02d}" for i in range(N_AGENT)], "true_speed_factor": np.round(speed, 4),
                       "true_rank": (ranks(speed) + 1).astype(int), "hard_share_pct": np.round(hard * 100, 2),
                       "avg_min": np.round(avg, 2), "avg_rank": (ranks(avg) + 1).astype(int),
                       "adjusted_ratio": np.round(adj, 4), "adjusted_rank": (ranks(adj) + 1).astype(int)})
    for k, name in enumerate(TYPES):
        ex[f"share_{name}_pct"] = np.round(np.bincount(agent, typ == k) / N_CASE * 100, 2)
    ex = ex.sort_values("avg_rank").reset_index(drop=True)
    ex.to_csv(RES / "example_month.csv", index=False)
    pd.DataFrame({"agent": [f"担当{a + 1:02d}" for a in agent], "type": [TYPES[k] for k in typ],
                  "minutes": np.round(t, 2)}).to_csv(DATA / "cases_example_month.csv", index=False)
    type_mean = [r(t[typ == k].mean(), 2) for k in range(len(TYPES))]
    out["example"] = {"rankcorr_raw": r(rank_corr(avg, speed), 3), "rankcorr_adj": r(rank_corr(adj, speed), 3),
                      "type_mean_min": type_mean,
                      "raw_fastest": ex.iloc[0][["agent", "avg_min", "hard_share_pct", "true_rank", "adjusted_rank"]].to_dict(),
                      "raw_slowest": ex.iloc[-1][["agent", "avg_min", "hard_share_pct", "true_rank", "adjusted_rank"]].to_dict(),
                      "true_fastest": ex[ex.true_rank == 1].iloc[0][["agent", "avg_min", "hard_share_pct", "avg_rank", "adjusted_rank"]].to_dict(),
                      "avg_min_min": r(avg.min(), 2), "avg_min_max": r(avg.max(), 2),
                      "hard_share_min_pct": r(hard.min() * 100, 2), "hard_share_max_pct": r(hard.max() * 100, 2),
                      "rankcorr_avg_vs_hard": r(rank_corr(avg, hard), 3)}

    out["base"] = summarize(rng, BASE["rho"], BASE["spread"], BASE["gamma"], R_BASE)
    print("base", round(time.time() - T0, 1), flush=True)

    rows = []
    for rho in RHOS:
        for sp in SPREADS:
            for g in GAMMAS:
                s = summarize(rng, rho, sp, g, R_GRID)
                rows.append({"rho": rho, "spread": sp, "gamma": g, **s})
        print("grid", rho, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    g0 = grid[grid.gamma == 0]
    wide0 = g0[g0.spread == "広い"].set_index("rho")
    out["grid"] = {"settings": len(grid),
                   "raw_min": grid.rankcorr_raw.min(), "raw_max": grid.rankcorr_raw.max(),
                   "adj_min_gamma0": g0.rankcorr_adj.min(), "adj_max_gamma0": g0.rankcorr_adj.max(),
                   "adj_min_all": grid.rankcorr_adj.min(), "adj_max_all": grid.rankcorr_adj.max(),
                   "adj_gt_raw_settings": int((grid.rankcorr_adj > grid.rankcorr_raw).sum()),
                   "same_mix_raw_min": grid[(grid.spread == "同じ")].rankcorr_raw.min(),
                   "same_mix_raw_max": grid[(grid.spread == "同じ")].rankcorr_raw.max(),
                   "wide_gamma0_raw_by_rho": {str(k): v for k, v in wide0.rankcorr_raw.items()},
                   "wide_gamma0_adj_by_rho": {str(k): v for k, v in wide0.rankcorr_adj.items()},
                   "wide_rho05_adj_by_gamma": {str(k): v for k, v in grid[(grid.spread == "広い") & (grid.rho == 0.5)].set_index("gamma").rankcorr_adj.items()},
                   "wide_rho05_raw_by_gamma": {str(k): v for k, v in grid[(grid.spread == "広い") & (grid.rho == 0.5)].set_index("gamma").rankcorr_raw.items()}}
    out["headline"] = {"rankcorr_raw": out["base"]["rankcorr_raw"], "rankcorr_adj": out["base"]["rankcorr_adj"],
                       "top5_hit_raw": out["base"]["top5_hit_raw"], "top5_hit_adj": out["base"]["top5_hit_adj"],
                       "raw_fastest_in_true_top5_pct": out["base"]["raw_fastest_in_true_top5_pct"]}

    # 図1：例の1か月（平均時間と種類をそろえた比）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    sc = axes[0].scatter(ex.hard_share_pct, ex.avg_min, c=ex.true_rank, cmap="viridis_r", s=40, vmin=1, vmax=20)
    axes[0].set_xlabel("難しい種類（C・D）の割合（%）")
    axes[0].set_ylabel("平均の対応時間（分）")
    axes[0].set_ylim(0, ex.avg_min.max() * 1.1)
    axes[0].set_xlim(0, 70)
    axes[0].set_title(f"平均の対応時間\n（本当の順との順位の相関 {out['example']['rankcorr_raw']:g}）", fontsize=10.5)
    axes[1].scatter(ex.true_speed_factor, ex.adjusted_ratio, c=ex.true_rank, cmap="viridis_r", s=40, vmin=1, vmax=20)
    lim = [min(ex.true_speed_factor.min(), ex.adjusted_ratio.min()) * 0.95, max(ex.true_speed_factor.max(), ex.adjusted_ratio.max()) * 1.05]
    axes[1].plot(lim, lim, color=GRAY, lw=1, ls="--")
    axes[1].set_xlabel("本当の倍率（作成者が置いた値、小さいほど手早い）")
    axes[1].set_ylabel("種類をそろえた比")
    axes[1].set_title(f"種類をそろえた比\n（本当の順との順位の相関 {out['example']['rankcorr_adj']:g}）", fontsize=10.5)
    cb = fig.colorbar(sc, ax=axes, shrink=0.85, ticks=[1, 5, 10, 15, 20])
    cb.set_label("本当の手早さの順位（1＝いちばん手早い）")
    cb.ax.invert_yaxis()
    save(fig, "a1186_example.png", SRC)

    # 図2：手早さと混ざり方の相関ごとの順位の相関（混ざり方の差が広い、見えない偏りなし）
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    x = np.arange(len(RHOS))
    vr = [wide0.loc[k, "rankcorr_raw"] for k in RHOS]
    va = [wide0.loc[k, "rankcorr_adj"] for k in RHOS]
    ax.bar(x - 0.2, vr, width=0.4, color=GRAY, label="平均の対応時間の順")
    ax.bar(x + 0.2, va, width=0.4, color=BLUE, label="種類をそろえた比の順")
    for i in range(len(RHOS)):
        ax.text(i - 0.2, vr[i] + (0.03 if vr[i] >= 0 else -0.08), f"{vr[i]:g}", ha="center", fontsize=8.5)
        ax.text(i + 0.2, va[i] + 0.03, f"{va[i]:g}", ha="center", fontsize=8.5, color=BLUE)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["手早いほど易しい\n（−0.5）", "関係なし\n（0）", "手早いほど難しい\n（0.5、基本）", "手早いほど難しい\n（0.8）"], fontsize=9)
    ax.set_ylim(-1, 1.12)
    ax.set_ylabel("本当の手早さの順との順位の相関")
    ax.set_xlabel("手早さと、難しい種類を受けやすいことの相関（混ざり方の差は広い）")
    ax.set_title("平均の時間の順は、混ざり方の配り方で当たりも外れもする（200回の平均）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1186_rankcorr.png", SRC, y=-0.05)

    # 図3：種類の中の見えない難しさの偏り
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    sub = grid[grid.spread == "広い"]
    cols = {-0.5: GRAY, 0.0: GREEN, 0.5: BLUE, 0.8: ORANGE}
    for t_, rho in enumerate(RHOS):
        v = [sub[(sub.rho == rho) & (sub.gamma == g)].rankcorr_adj.iloc[0] for g in GAMMAS]
        xs = np.arange(len(GAMMAS)) + (t_ - 1.5) * 0.2
        ax.bar(xs, v, width=0.2, color=cols[rho], label=f"相関 {rho:g}")
        for xx, vv in zip(xs, v):
            ax.text(xx, vv + (0.03 if vv >= 0 else -0.08), f"{vv:.2f}", ha="center", fontsize=7.5)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(len(GAMMAS)))
    ax.set_xticklabels([f"なし（0）", "少し（0.15）", "大きい（0.3）"])
    ax.set_ylim(-1, 1.12)
    ax.set_xlabel("難しい混ざり方の担当ほど、同じ種類の中でも難しい件を受ける偏り")
    ax.set_ylabel("種類をそろえた比の順と、本当の順の順位の相関")
    ax.set_title("種類で見えない難しさが偏ると、そろえても当たりにくい（混ざり方の差は広い）", fontsize=11)
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="lower left")
    save(fig, "a1186_hidden.png", SRC, y=-0.05)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1186_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
