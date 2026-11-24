"""1164 1か月の増え方を12倍した1年の見込みは、月による増え方の偏りでどれだけ外れるのか？（架空のデータ）

作成者が置いた架空のアプリの保存データ。1か月に増える量（GB）を
  増える量 = 100GB ×（1＋伸び）^（何か月目）× 季節の形（月ごと）× 振れ
と置いた。季節の形は 1＋A×cos（3月が山・9月が谷、12か月の平均はちょうど1）、振れは対数が正規の形（平均1）。
基本は A＝0.4、伸び＝月1%、振れ（対数の標準偏差）＝0.15。架空のアプリ2,000個（振れだけが違う）で、
2年目の各月（13〜24か月目）に「その月までの記録」から次の12か月の合計を見込み、実際の12か月の合計と比べる。
見込み方：(a) その月の増え方×12、(b) 直近3か月の平均×12、(c) 直近12か月の合計、(d) 直近12か月の合計×（その月÷前年同月）
確かめ：A（0・0.2・0.4・0.6）×伸び（月0・1・3%）×振れ（0.05・0.15・0.3）の36通り（各500個）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1164
SRC = "架空のアプリの保存データ（作成者が置いた季節の形・伸び・振れからの乱数、seed 1164）"
BASE_GB = 100.0
A_BASE, G_BASE, S_BASE = 0.4, 0.01, 0.15
N_APP, N_GRID = 2000, 500
N_MONTH = 36                      # 1〜36か月目（1か月目＝1月）
MEAS = np.arange(13, 25)          # 見込む月（2年目の1〜12月）
METHODS = [("a", "その月×12"), ("b", "直近3か月の平均×12"), ("c", "直近12か月の合計"),
           ("d", "直近12か月×（その月÷前年同月）")]
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def season(A, months):
    cal = (months - 1) % 12 + 1   # 暦の月
    return 1 + A * np.cos(2 * np.pi * (cal - 3) / 12)


def make(rng, n, A, g, s):
    t = np.arange(1, N_MONTH + 1)
    trend = BASE_GB * (1 + g) ** (t - 1)
    noise = np.exp(rng.normal(-s ** 2 / 2, s, (n, N_MONTH))) if s > 0 else np.ones((n, N_MONTH))
    return trend[None, :] * season(A, t)[None, :] * noise


def estimates(x):
    """x: (n, 36)。見込む月ごとに (n, 12) の比（見込み÷実際）を4つ返す"""
    out = {k: [] for k, _ in METHODS}
    for m in MEAS:
        i = m - 1
        true = x[:, i + 1:i + 13].sum(1)
        last12 = x[:, i - 11:i + 1].sum(1)
        out["a"].append(12 * x[:, i] / true)
        out["b"].append(4 * x[:, i - 2:i + 1].sum(1) / true)
        out["c"].append(last12 / true)
        out["d"].append(last12 * x[:, i] / x[:, i - 12] / true)
    return {k: np.stack(v, 1) for k, v in out.items()}


def within(v):
    """±20%に入ったか（ちょうど0.8・1.2も入れる。計算の丸めの差を吸収）"""
    return np.abs(v - 1) <= 0.2 + 1e-9


def summ(ratio):
    v = ratio.ravel()
    return {"median": r(np.median(v)), "p10": r(np.quantile(v, 0.1)), "p90": r(np.quantile(v, 0.9)),
            "mean": r(v.mean()), "within20_pct": r(within(v).mean() * 100, 2),
            "below1_pct": r((v < 1).mean() * 100, 2)}


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    t = np.arange(1, 13)
    s_m = season(A_BASE, t)
    out["setting"] = {"base_gb_month1": BASE_GB, "season_A": A_BASE, "growth_per_month_pct": G_BASE * 100,
                      "noise_sd_log": S_BASE, "apps": N_APP, "estimates_total": N_APP * len(MEAS),
                      "season_by_month": {int(m): r(v) for m, v in zip(t, s_m)},
                      "season_mean": r(s_m.mean()),
                      "growth_only_ratio_formula": r(12 / sum((1 + G_BASE) ** k for k in range(1, 13))),
                      "growth_only_last12_formula": r((1 + G_BASE) ** -12)}

    x = make(rng, N_APP, A_BASE, G_BASE, S_BASE)
    ex = pd.DataFrame(np.round(x[:20], 2), columns=[f"m{k:02d}" for k in range(1, N_MONTH + 1)])
    ex.insert(0, "app_id", np.arange(1, 21))
    ex.to_csv(DATA / "monthly_example.csv", index=False)

    est = estimates(x)
    base = {k: {"name": nm, **summ(est[k])} for k, nm in METHODS}
    out["base"] = base
    # 見込む月ごと（暦の月）
    rows = []
    for j, m in enumerate(MEAS):
        cal = (m - 1) % 12 + 1
        row = {"month": int(cal), "season_factor": r(s_m[cal - 1])}
        for k, _ in METHODS:
            v = est[k][:, j]
            row[f"{k}_median"] = r(np.median(v))
            row[f"{k}_p10"] = r(np.quantile(v, 0.1))
            row[f"{k}_p90"] = r(np.quantile(v, 0.9))
            row[f"{k}_within20_pct"] = r(within(v).mean() * 100, 2)
        rows.append(row)
    bym = pd.DataFrame(rows)
    bym.to_csv(RES / "base_by_month.csv", index=False)
    out["base_by_month_a"] = {"median_min": r(bym.a_median.min()), "median_max": r(bym.a_median.max()),
                              "month_min": int(bym.month[bym.a_median.idxmin()]),
                              "month_max": int(bym.month[bym.a_median.idxmax()]),
                              "within20_min": r(bym.a_within20_pct.min(), 2),
                              "within20_max": r(bym.a_within20_pct.max(), 2),
                              "months_within20_over50": int((bym.a_within20_pct > 50).sum())}

    # 分け方：季節だけ・伸びだけ・振れだけ・全部（(a) その月×12）
    parts = []
    for name, A, g, s in [("季節だけ", A_BASE, 0, 0), ("伸びだけ", 0, G_BASE, 0), ("振れだけ", 0, 0, S_BASE),
                          ("季節と伸び", A_BASE, G_BASE, 0), ("全部（基本）", A_BASE, G_BASE, S_BASE)]:
        e = est if name == "全部（基本）" else estimates(make(np.random.default_rng(SEED + len(parts) + 1), N_APP, A, g, s))
        d = {"case": name, "A": A, "growth_pct": g * 100, "noise": s}
        for k, _ in METHODS:
            sm = summ(e[k])
            d[f"{k}_median"], d[f"{k}_p10"], d[f"{k}_p90"] = sm["median"], sm["p10"], sm["p90"]
            d[f"{k}_within20_pct"] = sm["within20_pct"]
        d["a_min"] = r(e["a"].min())
        d["a_max"] = r(e["a"].max())
        parts.append(d)
    parts = pd.DataFrame(parts)
    parts.to_csv(RES / "parts.csv", index=False)
    out["parts"] = parts.to_dict(orient="records")
    # 季節だけのとき、(a) の比は季節の形そのもの（式どおり）
    e_s = estimates(make(np.random.default_rng(1), 1, A_BASE, 0, 0))["a"][0]
    cal = (MEAS - 1) % 12
    out["season_only_check_maxdiff"] = r(np.abs(e_s - s_m[cal]).max(), 10)
    print("base", round(time.time() - T0, 1), flush=True)

    # 確かめ：36通り
    rows = []
    gi = 0
    for A in [0, 0.2, 0.4, 0.6]:
        for g in [0, 0.01, 0.03]:
            for s in [0.05, 0.15, 0.3]:
                gi += 1
                e = estimates(make(np.random.default_rng(SEED * 100 + gi), N_GRID, A, g, s))
                d = {"A": A, "growth_pct": g * 100, "noise": s}
                for k, _ in METHODS:
                    sm = summ(e[k])
                    d[f"{k}_median"], d[f"{k}_within20_pct"] = sm["median"], sm["within20_pct"]
                rows.append(d)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    gs = {}
    for k, _ in METHODS:
        gs[k] = {"within20_min": r(grid[f"{k}_within20_pct"].min(), 2),
                 "within20_max": r(grid[f"{k}_within20_pct"].max(), 2),
                 "median_min": r(grid[f"{k}_median"].min()), "median_max": r(grid[f"{k}_median"].max())}
    best = grid[[f"{k}_within20_pct" for k, _ in METHODS]].idxmax(axis=1).str[0]
    gs["best_count"] = {k: int((best == k).sum()) for k, _ in METHODS}
    gs["a_worse_than_d"] = int((grid.a_within20_pct < grid.d_within20_pct).sum())
    gs["a_worse_than_b"] = int((grid.a_within20_pct < grid.b_within20_pct).sum())
    g3 = grid[grid.growth_pct == 3]
    gs["c_within20_growth3_max"] = r(g3.c_within20_pct.max(), 2)
    gs["c_median_growth3_max"] = r(g3.c_median.max())
    a6 = grid[grid.A == 0.6]
    gs["a_within20_A06_max"] = r(a6.a_within20_pct.max(), 2)
    a0 = grid[grid.A == 0]
    gs["a_within20_A0_min"] = r(a0.a_within20_pct.min(), 2)
    gs["a_within20_A0_max"] = r(a0.a_within20_pct.max(), 2)
    hs = grid[grid.noise == 0.3]
    gs["d_within20_noise03_max"] = r(hs.d_within20_pct.max(), 2)
    gs["b_within20_noise03_max"] = r(hs.b_within20_pct.max(), 2)
    out["grid"] = gs

    out["headline"] = {"a_median": base["a"]["median"], "a_p10": base["a"]["p10"], "a_p90": base["a"]["p90"],
                       "a_within20": base["a"]["within20_pct"],
                       "a_by_month_min": out["base_by_month_a"]["median_min"],
                       "a_by_month_max": out["base_by_month_a"]["median_max"],
                       "d_within20": base["d"]["within20_pct"], "c_median": base["c"]["median"]}

    # 図1：見込む月ごとの (a) の比
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    mm = bym.month.values
    order = np.argsort(mm)
    mo, med = mm[order], bym.a_median.values[order]
    ax.fill_between(mo, bym.a_p10.values[order], bym.a_p90.values[order], color=LIGHT, alpha=0.7,
                    label="その月×12（2,000個の10〜90%）")
    ax.plot(mo, med, color=BLUE, marker="o", label="その月×12（中央値）")
    ax.plot(mo, bym.d_median.values[order], color=GREEN, marker="s", ms=4,
            label="直近12か月×（その月÷前年同月）（中央値）")
    ax.axhline(1, color=INK, lw=1)
    ax.axhspan(0.8, 1.2, color=GRAY, alpha=0.12)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
    ax.set_ylim(0, max(bym.a_p90.max(), 1.5) * 1.1)
    ax.set_xlabel("見込みを立てた月")
    ax.set_ylabel("見込み ÷ 実際の次の12か月")
    ax.set_title("その月×12の見込みは、どの月に立てたかで上下する（灰色は±20%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    save(fig, "a1164_by_month.png", SRC)

    # 図2：見込み方ごとの ±20% に入った割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    names = [nm for _, nm in METHODS]
    vals = [base[k]["within20_pct"] for k, _ in METHODS]
    ax.bar(range(4), vals, color=[BLUE, GRAY, ORANGE, GREEN])
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:g}%", ha="center", fontsize=9.5)
    ax.set_xticks(range(4))
    ax.set_xticklabels([n.replace("×（", "\n×（") for n in names], fontsize=8.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("実際の±20%に入った割合（%）")
    ax.set_title("基本の置き方で、見込み方ごとに±20%に入った割合（12か月×2,000個）")
    save(fig, "a1164_methods.png", SRC)

    # 図3：36通りで (a) と (d) の ±20%
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.9), sharey=True)
    for ax, g in zip(axes, [0, 1, 3]):
        sub = grid[grid.growth_pct == g]
        for k, col, nm in [("a", BLUE, "その月×12"), ("d", GREEN, "直近12か月×前年同月比")]:
            for s, ls in [(0.05, ":"), (0.15, "-"), (0.3, "--")]:
                q = sub[sub.noise == s]
                ax.plot(q.A, q[f"{k}_within20_pct"], color=col, ls=ls, marker="o", ms=3.5,
                        label=f"{nm}・振れ{s:g}" if g == 0 else None)
        ax.set_title(f"伸び 月{g}%", fontsize=11)
        ax.set_xticks([0, 0.2, 0.4, 0.6])
        ax.set_xlabel("季節の偏り A")
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("±20%に入った割合（%）")
    fig.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.07), ncol=3)
    fig.suptitle("36通り：季節の偏りが大きいほど、その月×12は外れやすい", y=1.13, fontsize=12)
    save(fig, "a1164_grid.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1164_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
