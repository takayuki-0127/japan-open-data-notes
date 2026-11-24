"""1171 中身の種類で圧縮のかかり方が違うとき、種類の割合が変わると全体の圧縮率はどう動くのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル。中身の種類は 文章・記録・表・画像 の4つで、種類ごとに大きさの分布と
縮み方（圧縮後÷圧縮前の中央値）を置いた。画像はすでに縮めてあるのでほとんど縮まない。
全体の圧縮率（圧縮後の合計÷圧縮前の合計）は、種類ごとの率を「量（バイト）の割合」で重みを付けた平均にちょうどなる（式どおり）。
(1) 今年：量の割合 文章10%・記録40%・表30%・画像20%（元の量の合計500GB）
(2) 来年の3通り：A 画像の量が40%に増える／B Aに加えて、どの種類も縮み方が1割よくなる／C 件数の割合は今年のまま、画像1件が1.5倍に大きくなる
    来年の圧縮後の合計を ①今年の全体の率×来年の元の量 ②種類ごとの今年の率×来年の種類ごとの元の量 で見込み、実際と比べる
(3) 確かめ：来年の画像の量の割合（10〜60%の6通り）×画像の縮み方の中央値（0.5・0.75・0.97の3通り）の18通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1171
SRC = "架空のアプリの保存ファイル（作成者が置いた種類ごとの大きさと縮み方からの乱数、seed 1171）"
TYPES = ["文章", "記録", "表", "画像"]
KEYS = ["text", "log", "table", "image"]
MED_KB = {"text": 50.0, "log": 2000.0, "table": 500.0, "image": 1500.0}
SIG = {"text": 1.2, "log": 1.0, "table": 1.2, "image": 0.8}
Q_MED = {"text": 0.25, "log": 0.12, "table": 0.40, "image": 0.97}
Q_SIG = 0.15
TOTAL_GB = 500.0
SHARE0 = {"text": 0.10, "log": 0.40, "table": 0.30, "image": 0.20}
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def mean_kb(k, scale=1.0):
    return MED_KB[k] * scale * np.exp(SIG[k] ** 2 / 2)


def counts_for(shares, img_scale=1.0):
    return {k: int(round(shares[k] * TOTAL_GB * 1e6 / mean_kb(k, img_scale if k == "image" else 1.0))) for k in KEYS}


def make_year(rng, counts, img_scale=1.0, qmul=1.0, q_img=None):
    out = {}
    for k in KEYS:
        n = counts[k]
        size = rng.lognormal(np.log(MED_KB[k] * (img_scale if k == "image" else 1.0)), SIG[k], n)
        qm = Q_MED[k] if not (k == "image" and q_img is not None) else q_img
        q = np.minimum(qm * qmul * np.exp(Q_SIG * rng.standard_normal(n)), 1.0)
        out[k] = (size, q * size)
    return out


def summary(year):
    rows = {}
    tot_o = sum(year[k][0].sum() for k in KEYS)
    tot_c = sum(year[k][1].sum() for k in KEYS)
    n_all = sum(len(year[k][0]) for k in KEYS)
    for k in KEYS:
        o, c = year[k]
        rows[k] = {"files": len(o), "count_share": len(o) / n_all, "orig_gb": o.sum() / 1e6,
                   "byte_share": o.sum() / tot_o, "rate": c.sum() / o.sum(), "comp_gb": c.sum() / 1e6}
    return rows, tot_o / 1e6, tot_c / 1e6


def estimates(this_rows, this_rate, next_rows, next_o, next_c):
    e1 = this_rate * next_o
    e2 = sum(this_rows[k]["rate"] * next_rows[k]["orig_gb"] for k in KEYS)
    return {"actual_comp_gb": r(next_c, 3), "actual_rate_pct": r(next_c / next_o * 100, 2),
            "m1_overall_rate_gb": r(e1, 3), "m1_ratio": r(e1 / next_c),
            "m2_by_type_gb": r(e2, 3), "m2_ratio": r(e2 / next_c)}


def shares_with_image(s_img):
    rest = 1 - SHARE0["image"]
    return {k: (s_img if k == "image" else SHARE0[k] * (1 - s_img) / rest) for k in KEYS}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"types": dict(zip(KEYS, TYPES)), "median_kb": MED_KB, "sigma_log_size": SIG,
                       "q_median": Q_MED, "q_sigma_log": Q_SIG, "total_orig_gb_target": TOTAL_GB,
                       "byte_share_this_year_target": SHARE0}}
    c0 = counts_for(SHARE0)
    y0 = make_year(rng, c0)
    rows0, o0, cc0 = summary(y0)
    rate0 = cc0 / o0
    wsum = sum(rows0[k]["byte_share"] * rows0[k]["rate"] for k in KEYS)
    out["this_year"] = {"by_type": {k: {kk: r(v, 4) for kk, v in rows0[k].items()} for k in KEYS},
                        "orig_gb": r(o0, 3), "comp_gb": r(cc0, 3), "overall_rate_pct": r(rate0 * 100, 2),
                        "byte_weighted_rate_pct": r(wsum * 100, 2),
                        "count_weighted_rate_pct": r(sum(rows0[k]["count_share"] * rows0[k]["rate"] for k in KEYS) * 100, 2),
                        "file_mean_rate_pct": r(np.concatenate([y0[k][1] / y0[k][0] for k in KEYS]).mean() * 100, 2)}
    # data：今年のファイルから種類を問わず 5,000件
    allk = np.concatenate([[k] * len(y0[k][0]) for k in KEYS])
    allo = np.concatenate([y0[k][0] for k in KEYS])
    allc = np.concatenate([y0[k][1] for k in KEYS])
    idx = np.sort(rng.choice(len(allo), 5000, replace=False))
    pd.DataFrame({"file_id": np.arange(1, 5001), "kind": allk[idx], "orig_kb": np.round(allo[idx], 2),
                  "comp_kb": np.round(allc[idx], 2)}).to_csv(DATA / "files_this_year_sample.csv", index=False)

    # (2) 来年の3通り
    scen = {}
    sA = shares_with_image(0.40)
    yA = make_year(rng, counts_for(sA))
    yB = make_year(rng, counts_for(sA), qmul=0.9)
    yC = make_year(rng, {k: int(round(c0[k] * TOTAL_GB / TOTAL_GB)) for k in KEYS}, img_scale=1.5)
    tbl = []
    for key, name, y in [("A", "画像の量が40%に", yA), ("B", "Aに加え、どの種類も縮み方が1割よくなる", yB),
                         ("C", "件数の割合は同じ、画像1件が1.5倍", yC)]:
        rows, o, c = summary(y)
        est = estimates(rows0, rate0, rows, o, c)
        scen[key] = {"name": name, "orig_gb": r(o, 3),
                     "by_type": {k: {kk: r(v, 4) for kk, v in rows[k].items()} for k in KEYS}, **est}
        for k in KEYS:
            tbl.append({"scenario": key, "kind": k, "files": rows[k]["files"], "count_share_pct": r(rows[k]["count_share"] * 100, 2),
                        "byte_share_pct": r(rows[k]["byte_share"] * 100, 2), "rate_pct": r(rows[k]["rate"] * 100, 2)})
    for k in KEYS:
        tbl.append({"scenario": "this_year", "kind": k, "files": rows0[k]["files"], "count_share_pct": r(rows0[k]["count_share"] * 100, 2),
                    "byte_share_pct": r(rows0[k]["byte_share"] * 100, 2), "rate_pct": r(rows0[k]["rate"] * 100, 2)})
    pd.DataFrame(tbl).to_csv(RES / "by_type.csv", index=False)
    out["next_year"] = scen
    out["B_each_type_better"] = {k: r((scen["B"]["by_type"][k]["rate"] - rows0[k]["rate"]) * 100, 2) for k in KEYS}
    print("scen", round(time.time() - T0, 1), flush=True)

    # 1か月ごとに画像の量の割合が20%→40%に動く（12か月、1か月の元の量は500GB÷12）
    months = []
    for m in range(13):
        s_img = 0.20 + 0.20 * m / 12
        sh = shares_with_image(s_img)
        cm = {k: max(1, int(round(v / 12))) for k, v in counts_for(sh).items()}
        ym = make_year(rng, cm)
        rows, o, c = summary(ym)
        months.append({"month": m, "image_byte_share_target_pct": r(s_img * 100, 2),
                       "image_byte_share_pct": r(rows["image"]["byte_share"] * 100, 2),
                       "overall_rate_pct": r(c / o * 100, 2),
                       "formula_rate_pct": r(sum(sh[k] * rows0[k]["rate"] for k in KEYS) * 100, 2)})
    months = pd.DataFrame(months)
    months.to_csv(RES / "monthly.csv", index=False)
    out["monthly"] = {"rate_first_pct": float(months.overall_rate_pct.iloc[0]),
                      "rate_last_pct": float(months.overall_rate_pct.iloc[-1]),
                      "max_abs_diff_formula_pt": r((months.overall_rate_pct - months.formula_rate_pct).abs().max(), 2)}

    # (3) 18通り
    grid = []
    for qi in [0.5, 0.75, 0.97]:
        c_this = counts_for(SHARE0)
        yt = make_year(rng, c_this, q_img=qi)
        rt, ot, ct = summary(yt)
        for s_img in [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]:
            yn = make_year(rng, counts_for(shares_with_image(s_img)), q_img=qi)
            rn, on, cn = summary(yn)
            est = estimates(rt, ct / ot, rn, on, cn)
            grid.append({"image_q_median": qi, "image_byte_share_next_pct": s_img * 100,
                         "this_rate_pct": r(ct / ot * 100, 2),
                         "image_rate_this_pct": r(rt["image"]["rate"] * 100, 2), **est})
        print("grid", qi, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"settings": len(grid), "actual_rate_min": r(grid.actual_rate_pct.min(), 2),
                   "actual_rate_max": r(grid.actual_rate_pct.max(), 2),
                   "m1_ratio_min": r(grid.m1_ratio.min()), "m1_ratio_max": r(grid.m1_ratio.max()),
                   "m2_ratio_min": r(grid.m2_ratio.min()), "m2_ratio_max": r(grid.m2_ratio.max()),
                   "same_share_m1_ratio_min": r(grid[grid.image_byte_share_next_pct == 20].m1_ratio.min()),
                   "same_share_m1_ratio_max": r(grid[grid.image_byte_share_next_pct == 20].m1_ratio.max())}
    out["headline"] = {"this_rate_pct": out["this_year"]["overall_rate_pct"], "A_rate_pct": scen["A"]["actual_rate_pct"],
                       "A_m1_ratio": scen["A"]["m1_ratio"], "B_rate_pct": scen["B"]["actual_rate_pct"],
                       "C_rate_pct": scen["C"]["actual_rate_pct"], "C_m1_ratio": scen["C"]["m1_ratio"],
                       "grid_m1_min": out["grid"]["m1_ratio_min"], "grid_m1_max": out["grid"]["m1_ratio_max"]}

    # 図1：種類ごとの率と量の割合（今年・A）
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.0))
    xs = np.arange(4)
    rates = [rows0[k]["rate"] * 100 for k in KEYS]
    axs[0].bar(xs, rates, color=BLUE)
    for x, v in zip(xs, rates):
        axs[0].text(x, v + 1.5, f"{v:.2f}%", ha="center", fontsize=9)
    axs[0].set_xticks(xs); axs[0].set_xticklabels(TYPES)
    axs[0].set_ylim(0, 110); axs[0].set_ylabel("種類ごとの圧縮率（圧縮後÷圧縮前、%）")
    axs[0].set_title("種類ごとの縮み方（今年）", fontsize=11)
    w = 0.38
    s_this = [rows0[k]["byte_share"] * 100 for k in KEYS]
    s_A = [scen["A"]["by_type"][k]["byte_share"] * 100 for k in KEYS]
    axs[1].bar(xs - w / 2, s_this, width=w, color=GRAY, label="今年")
    axs[1].bar(xs + w / 2, s_A, width=w, color=ORANGE, label="来年A")
    for x, a, b2 in zip(xs, s_this, s_A):
        axs[1].text(x - w / 2, a + 1, f"{a:.2f}", ha="center", fontsize=7.5)
        axs[1].text(x + w / 2, b2 + 1, f"{b2:.2f}", ha="center", fontsize=7.5)
    axs[1].set_xticks(xs); axs[1].set_xticklabels(TYPES)
    axs[1].set_ylim(0, 50); axs[1].set_ylabel("元の量に占める割合（%）")
    axs[1].set_title(f"全体の率 今年{rate0 * 100:.2f}% → 来年A {scen['A']['actual_rate_pct']:g}%", fontsize=11)
    axs[1].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    save(fig, "a1171_rate_share.png", SRC)

    # 図2：見込み÷実際（3通り×3つの見込み方）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    labs = ["A 画像の量が40%に", "B Aに加え\n各種類1割よく縮む", "C 件数の割合は同じ\n画像1件1.5倍"]
    w = 0.34
    for j, (m, lab, col) in enumerate([("m1", "①今年の全体の率×来年の元の量", BLUE), ("m2", "②種類ごとの今年の率×来年の種類ごとの量", GREEN)]):
        vals = [scen[s][f"{m}_ratio"] for s in "ABC"]
        xs = np.arange(3) + (j - 0.5) * w
        ax.bar(xs, vals, width=w, color=col, label=lab)
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.02, f"{v:g}", ha="center", fontsize=8)
    ax.axhline(1, color=INK, lw=1)
    ax.set_xticks(range(3)); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylim(0, 1.35)
    ax.set_ylabel("圧縮後の合計の見込み ÷ 実際")
    ax.set_title("来年の圧縮後の量の見込み（1倍が当たり）", pad=26)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, "a1171_estimates.png", SRC)

    # 図3：18通り（①の見込み÷実際）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for qi, col in zip([0.5, 0.75, 0.97], [GREEN, BLUE, ORANGE]):
        g = grid[grid.image_q_median == qi]
        ax.plot(g.image_byte_share_next_pct, g.m1_ratio, marker="o", color=col, label=f"画像の圧縮率 {g.image_rate_this_pct.iloc[0]:.1f}%")
    ax.axhline(1, color=INK, lw=1)
    ax.axvline(20, color=GRAY, lw=1, ls="--")
    ax.text(20.5, 0.03, "今年の画像の割合（20%）", color=GRAY, fontsize=8.5, transform=ax.get_xaxis_transform())
    ax.set_xlabel("来年の画像の量の割合（%）")
    ax.set_ylabel("①今年の全体の率での見込み ÷ 実際")
    ax.set_title("画像の割合が今年から離れるほど、①の見込みは外れる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1171_grid_m1.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1171_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
