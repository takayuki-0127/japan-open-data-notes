"""1212 道ぞいの区画だけを数えると、道から離れた所を好む生き物はどれだけ少なく出るのか？（架空のデータ）

作成者が置いた架空の森「A森」（2km四方を50m四方の区画1,600個に分けたもの）に、
道を横に3本通し、3つの架空の種の多さを「道からの距離」で置く。
  種A：道を気にしない（どこでも同じ）
  種B：道から離れた所を好む（道ぞいで少なく、離れるほど多い）
  種C：道ぞいの明るい所を好む（道ぞいで多い）
区画ごとの数は、置いた多さに区画ごとのむらを掛けた値を平均とする数の乱数。
40区画を数えて森全体の数を見込む（平均×1,600）とき、道ぞいの区画だけから選ぶと
本当の数の何倍に出るかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1212
SRC = "架空の森（作成者が乱数で作成、seed 1212）"
SIDE = 2000.0            # 森の一辺（m）
CELL = 50.0              # 区画の一辺（m）
NC = int(SIDE / CELL)    # 一辺の区画の数（40）
N_CELL = NC * NC         # 1,600区画
PATCH_SD = 0.5           # 区画ごとのむら（対数での標準偏差、平均1にそろえる）
N_SURVEY = 40            # 数える区画の数
REPS = 1000              # 森を作り直す回数
SPECIES = ["種A", "種B", "種C"]
BASE = dict(L=150.0, roads=3, band=50.0)


def r(x, d=3):
    return round(float(x), d)


def q(a, p):
    return float(np.quantile(a, p))


def road_ys(k):
    """横の道 k 本の位置（m）。50m の区画の境目に置く"""
    return [round(SIDE * (i + 0.5) / k / CELL) * CELL for i in range(k)]


def dist_map(k):
    yc = (np.arange(NC) + 0.5) * CELL
    d_row = np.min(np.abs(yc[:, None] - np.array(road_ys(k))[None, :]), axis=1)
    return np.repeat(d_row[:, None], NC, axis=1).ravel()   # 区画ごとの道からの距離


def density(d, L):
    """置いた多さ（1区画あたりの平均の数、むらの前）"""
    a = np.full_like(d, 4.0)
    b = 8.0 * (1 - np.exp(-d / L))
    c = 1.0 + 6.0 * np.exp(-d / 80.0)
    return np.vstack([a, b, c])          # 3×区画


def formula_ratio(lam, band_mask):
    """道ぞいだけの平均×区画数 ÷ 全体の数（置いた多さからの式）"""
    return lam[:, band_mask].mean(axis=1) / lam.mean(axis=1)


def one_forest(rng, lam):
    patch = np.exp(rng.normal(-PATCH_SD ** 2 / 2, PATCH_SD, lam.shape[1]))
    return rng.poisson(lam * patch[None, :])


def estimates(rng, cnt, band_mask, n=N_SURVEY):
    """3つの数え方で森全体の数を見込む"""
    idx_band = np.flatnonzero(band_mask)
    idx_far = np.flatnonzero(~band_mask)
    w_band = band_mask.mean()
    s1 = rng.choice(idx_band, n, replace=False)
    s2 = rng.choice(N_CELL, n, replace=False)
    h = n // 2
    s3a = rng.choice(idx_band, h, replace=False)
    e1 = cnt[:, s1].mean(axis=1) * N_CELL
    e2 = cnt[:, s2].mean(axis=1) * N_CELL
    if len(idx_far) == 0:       # 森のすべてが道ぞいのとき
        return e1, e2, e1
    s3b = rng.choice(idx_far, n - h, replace=False)
    e3 = (w_band * cnt[:, s3a].mean(axis=1) + (1 - w_band) * cnt[:, s3b].mean(axis=1)) * N_CELL
    return e1, e2, e3


METHODS = ["道ぞいの区画だけ", "森全体からでたらめに", "道ぞい半分＋離れた所半分（面積で重み）"]


def run(rng, L, roads, band, reps, n=N_SURVEY, keep=False):
    d = dist_map(roads)
    lam = density(d, L)
    band_mask = d <= band
    ratios = np.zeros((3, reps, 3))      # 数え方×回×種
    shares = np.zeros((4, reps))         # 本当と3つの数え方での種Bの割合
    tops = np.zeros((4, reps), dtype=int)  # 本当と3つの数え方でいちばん多い種
    first = None
    for i in range(reps):
        cnt = one_forest(rng, lam)
        true = cnt.sum(axis=1).astype(float)
        es = estimates(rng, cnt, band_mask, n)
        for m, e in enumerate(es):
            ratios[m, i] = e / true
            shares[m + 1, i] = e[1] / e.sum()
            tops[m + 1, i] = int(np.argmax(e))
        shares[0, i] = true[1] / true.sum()
        tops[0, i] = int(np.argmax(true))
        if keep and i == 0:
            first = cnt
    return dict(d=d, lam=lam, band_mask=band_mask, ratios=ratios, shares=shares, tops=tops,
                formula=formula_ratio(lam, band_mask), first=first)


def main():
    rng = np.random.default_rng(SEED)
    out = {"setup": {"cells": N_CELL, "cell_m": CELL, "survey_cells": N_SURVEY, "reps": REPS,
                     "road_y_m": road_ys(BASE["roads"]), **BASE}}

    # ---- 基本の置き方 ----
    base = run(rng, BASE["L"], BASE["roads"], BASE["band"], REPS, keep=True)
    rows = []
    for m, name in enumerate(METHODS):
        for s, sp in enumerate(SPECIES):
            x = base["ratios"][m, :, s]
            rows.append({"数え方": name, "種": sp, "本当の数に対する倍率_平均": r(x.mean()),
                         "倍率_10%点": r(q(x, 0.1)), "倍率_90%点": r(q(x, 0.9)),
                         "0.5倍未満の割合%": r((x < 0.5).mean() * 100, 2)})
    base_df = pd.DataFrame(rows)
    base_df.to_csv(RES / "base_ratios.csv", index=False)
    sh = base["shares"]
    out["base"] = {
        "band_share_of_forest_pct": r(base["band_mask"].mean() * 100, 2),
        "band_cells": int(base["band_mask"].sum()),
        "formula_ratio_roadside": {sp: r(v) for sp, v in zip(SPECIES, base["formula"])},
        "true_mean_count": {sp: r(v, 1) for sp, v in zip(SPECIES, base["lam"].sum(axis=1))},
        "shareB_pct": {"本当": r(sh[0].mean() * 100, 2),
                       **{METHODS[m]: r(sh[m + 1].mean() * 100, 2) for m in range(3)}},
        "shareB_roadside_10_90_pct": [r(q(sh[1], 0.1) * 100, 2), r(q(sh[1], 0.9) * 100, 2)],
        "top_species_pct": {k: {sp: r((base["tops"][m] == s).mean() * 100, 2) for s, sp in enumerate(SPECIES)}
                            for m, k in enumerate(["本当"] + METHODS)},
    }
    # 道からの距離ごとの1区画あたりの数（基本の森の1回分）
    d = base["d"]
    by_d = []
    for dv in np.unique(d):
        msk = d == dv
        by_d.append({"道からの距離m": int(dv), "区画の数": int(msk.sum()),
                     **{f"{sp}_置いた平均": r(base["lam"][s, msk].mean(), 3) for s, sp in enumerate(SPECIES)},
                     **{f"{sp}_1回分の平均": r(base["first"][s, msk].mean(), 3) for s, sp in enumerate(SPECIES)}})
    pd.DataFrame(by_d).to_csv(RES / "by_distance.csv", index=False)
    cells = pd.DataFrame({"cell_id": np.arange(N_CELL), "x_m": (np.arange(N_CELL) % NC + 0.5) * CELL,
                          "y_m": (np.arange(N_CELL) // NC + 0.5) * CELL, "dist_road_m": d.astype(int),
                          "roadside": base["band_mask"].astype(int),
                          **{f"count_{k}": base["first"][s] for s, k in enumerate("ABC")}})
    cells.to_csv(DATA / "forest_cells.csv", index=False)

    # ---- 数える区画の数（道ぞいだけ、種B） ----
    nn = []
    for n in [20, 40, 100]:
        rr = run(rng, BASE["L"], BASE["roads"], BASE["band"], 400, n=n)
        for m in [0, 1]:
            x = rr["ratios"][m, :, 1]
            nn.append({"数える区画": n, "数え方": METHODS[m], "種Bの倍率_平均": r(x.mean()),
                       "10%点": r(q(x, 0.1)), "90%点": r(q(x, 0.9))})
    pd.DataFrame(nn).to_csv(RES / "by_survey_size.csv", index=False)
    out["by_survey_size"] = nn

    # ---- 確かめ：好みの強さ×道の本数×道ぞいの幅 の27通り ----
    grid = []
    for L in [50.0, 150.0, 400.0]:
        for roads in [1, 3, 6]:
            for band in [50.0, 100.0, 200.0]:
                rr = run(rng, L, roads, band, 200)
                x = rr["ratios"][0]
                grid.append({"好みの距離L_m": int(L), "道の本数": roads, "道ぞいの幅m": int(band),
                             "道ぞいの面積%": r(rr["band_mask"].mean() * 100, 2),
                             "種B_式": r(rr["formula"][1]), "種B_平均": r(x[:, 1].mean()),
                             "種C_式": r(rr["formula"][2]), "種C_平均": r(x[:, 2].mean()),
                             "種A_平均": r(x[:, 0].mean()),
                             "種Bの割合_本当%": r(rr["shares"][0].mean() * 100, 2),
                             "種Bの割合_道ぞい%": r(rr["shares"][1].mean() * 100, 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"n": len(g), "B_mean_min": r(g["種B_平均"].min()), "B_mean_max": r(g["種B_平均"].max()),
                   "B_formula_min": r(g["種B_式"].min()), "B_formula_max": r(g["種B_式"].max()),
                   "C_mean_min": r(g["種C_平均"].min()), "C_mean_max": r(g["種C_平均"].max()),
                   "A_mean_min": r(g["種A_平均"].min()), "A_mean_max": r(g["種A_平均"].max()),
                   "max_abs_gap_B_sim_vs_formula": r((g["種B_平均"] - g["種B_式"]).abs().max(), 4),
                   "B_below_half_count": int((g["種B_平均"] < 0.5).sum()),
                   "B_band60pct_range": [r(g[g["道ぞいの面積%"] == 60]["種B_平均"].min()), r(g[g["道ぞいの面積%"] == 60]["種B_平均"].max())],
                   "B_band50_L150": g[(g["好みの距離L_m"] == 150) & (g["道ぞいの幅m"] == 50)][["道の本数", "種B_平均"]].to_dict("records")}

    # ---- 図1：森の地図（種Bの1回分の数と道ぞいの区画） ----
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    fig.subplots_adjust(wspace=0.45)
    for ax, s, ttl in [(axs[0], 1, "種B（道から離れた所を好む）"), (axs[1], 2, "種C（道ぞいを好む）")]:
        img = base["first"][s].reshape(NC, NC)
        im = ax.imshow(img, origin="lower", extent=[0, SIDE, 0, SIDE], cmap="Blues", vmin=0, vmax=np.quantile(img, 0.98))
        for y in road_ys(BASE["roads"]):
            ax.axhline(y, color=ORANGE, lw=2)
            ax.axhspan(y - BASE["band"], y + BASE["band"], color=ORANGE, alpha=0.18, lw=0)
        ax.set_title(f"{ttl}の1区画あたりの数", fontsize=11)
        ax.set_xlabel("m"); ax.set_ylabel("m")
        fig.colorbar(im, ax=ax, shrink=0.8, label="1区画の数（匹・羽）")
    fig.suptitle(f"架空のA森（1回分）：オレンジの線が道、薄いオレンジが道ぞいの区画（森の{base['band_mask'].mean()*100:.0f}%）", fontsize=12)
    save(fig, "a1212_map.png", SRC)

    # ---- 図2：数え方ごとの倍率 ----
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    wdt = 0.26
    cols = [ORANGE, BLUE, GREEN]
    for m in range(3):
        vals = [base_df[(base_df["数え方"] == METHODS[m]) & (base_df["種"] == sp)]["本当の数に対する倍率_平均"].iloc[0] for sp in SPECIES]
        xs = np.arange(3) + (m - 1) * wdt
        ax.bar(xs, vals, wdt, color=cols[m], label=METHODS[m])
        for xx, v in zip(xs, vals):
            ax.text(xx, v + 0.04, f"{v:g}", ha="center", fontsize=8.5)
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(["種A（道を気にしない）", "種B（離れた所を好む）", "種C（道ぞいを好む）"])
    ax.set_ylim(0, max(base_df["本当の数に対する倍率_平均"]) * 1.15)
    ax.set_ylabel("見込んだ数 ÷ 本当の数（1,000回の平均）")
    ax.set_title("40区画から森全体の数を見込んだ倍率（1が本当の数）")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1212_ratios.png", SRC)

    # ---- 図3：27通りの種Bの倍率と道ぞいの面積 ----
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for L, c in zip([50, 150, 400], [LIGHT, BLUE, INK]):
        gg = g[g["好みの距離L_m"] == L]
        ax.scatter(gg["道ぞいの面積%"], gg["種B_平均"], color=c, s=40, label=f"好みの距離 {L}m", zorder=3)
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_xlim(0, 100); ax.set_ylim(0, 1.1)
    ax.set_xlabel("道ぞいの区画が森に占める面積（%）")
    ax.set_ylabel("種Bの見込み ÷ 本当の数")
    ax.set_title("道ぞいだけで数えた種Bの倍率（27通り、各200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1212_grid.png", SRC)

    with open(RES / "a1212_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(base_df.to_string()); print(json.dumps(out, ensure_ascii=False, indent=1))
    print(g.to_string())


if __name__ == "__main__":
    main()
