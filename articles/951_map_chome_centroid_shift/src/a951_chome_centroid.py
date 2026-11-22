"""951 住所の「丁目」でまとめると、何がずれるのか？（架空のデータ）

架空の町（2,000m×2,000m）。町を4つの「町」（A町〜D町）に分け、それぞれをさらに長方形の「丁目」に
分ける（作成者が乱数で決めた架空の番地の付け方）。客の住む場所を作成者が置き、
客の場所を「丁目の真ん中（代表点）」に置き換えると、店からの距離・半径の中の客の数・
2店のどちらが近いかが、本当の場所で数えたときとどれだけずれるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 951
SRC = "架空の町の丁目と客の場所（作成者が乱数で作成、seed 951）"
L = 2000.0                       # 町の一辺（m）
BASE = {"n_cust": 3000, "n_chome": 48, "radius": 500.0, "dense_share": 0.6, "dense_sd": 250.0,
        "rep": "丁目の真ん中"}
DENSE = [(650.0, 1350.0), (1400.0, 700.0)]   # 客が集まる2か所（架空）
N_STORE = 300
TOWNS = ["A町", "B町", "C町", "D町"]


def make_chome(rng, n_chome):
    """町を4つの町に分け、各町を長方形の丁目に分ける（いちばん大きい丁目を、長い辺に沿ってでたらめな位置で2つに切る）"""
    cx, cy = rng.uniform(0.35, 0.65) * L, rng.uniform(0.35, 0.65) * L
    towns = [(0, cx, cy, L), (cx, L, cy, L), (0, cx, 0, cy), (cx, L, 0, cy)]   # A:左上 B:右上 C:左下 D:右下
    pieces = [[t] for t in towns]
    area = lambda r: (r[1] - r[0]) * (r[3] - r[2])
    while sum(len(p) for p in pieces) < n_chome:
        ti, ri = max(((i, j) for i, p in enumerate(pieces) for j in range(len(p))),
                     key=lambda ij: area(pieces[ij[0]][ij[1]]))
        x0, x1, y0, y1 = pieces[ti].pop(ri)
        f = rng.uniform(0.3, 0.7)
        if (x1 - x0) >= (y1 - y0):
            xm = x0 + f * (x1 - x0); pieces[ti] += [(x0, xm, y0, y1), (xm, x1, y0, y1)]
        else:
            ym = y0 + f * (y1 - y0); pieces[ti] += [(x0, x1, y0, ym), (x0, x1, ym, y1)]
    rows = []
    for t, p in zip(TOWNS, pieces):
        p = sorted(p, key=lambda r: (-r[3], r[0]))          # 上から、左から番号を付ける
        for k, (x0, x1, y0, y1) in enumerate(p):
            rows.append({"chome": f"{t}{k + 1}丁目", "town": t, "x0": x0, "x1": x1, "y0": y0, "y1": y1,
                         "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2})
    return pd.DataFrame(rows)


def make_customers(rng, n_cust, dense_share, dense_sd):
    n_d = rng.binomial(n_cust, dense_share)
    which = rng.integers(0, len(DENSE), n_d)
    pts = np.array(DENSE)[which] + rng.normal(0, dense_sd, (n_d, 2))
    pts = np.vstack([pts, rng.uniform(0, L, (n_cust - n_d, 2))])
    bad = (pts < 0) | (pts > L)
    while bad.any():                                         # 町の外に出た客は引き直す
        idx = bad.any(1)
        pts[idx] = rng.uniform(0, L, (idx.sum(), 2))
        bad = (pts < 0) | (pts > L)
    return pts


def assign(pts, ch):
    x, y = pts[:, 0:1], pts[:, 1:2]
    inside = (x >= ch.x0.values) & (x < ch.x1.values + 1e-9) & (y >= ch.y0.values) & (y < ch.y1.values + 1e-9)
    return inside.argmax(1)


def rep_points(pts, idx, ch, rep):
    if rep == "丁目の真ん中":
        r = ch[["cx", "cy"]].values
    else:                                                    # 客の重心（その丁目の客の平均の場所）
        r = ch[["cx", "cy"]].values.copy()
        for k in range(len(ch)):
            m = idx == k
            if m.any():
                r[k] = pts[m].mean(0)
    return r[idx]


def evaluate(rng, pts, rp, radius, n_store=N_STORE):
    """店をでたらめな場所に n_store 回置き、距離・半径の中の人数・2店のどちらが近いかのずれを数える"""
    stores = rng.uniform(0.1 * L, 0.9 * L, (n_store, 2))
    stores2 = rng.uniform(0.1 * L, 0.9 * L, (n_store, 2))
    d_true = np.hypot(pts[None, :, 0] - stores[:, None, 0], pts[None, :, 1] - stores[:, None, 1])
    d_rep = np.hypot(rp[None, :, 0] - stores[:, None, 0], rp[None, :, 1] - stores[:, None, 1])
    c_true = (d_true <= radius).sum(1)
    c_rep = (d_rep <= radius).sum(1)
    ratio = c_rep / np.maximum(c_true, 1) - 1
    miss = ((d_true <= radius) & (d_rep > radius)).sum(1) / np.maximum(c_true, 1)
    extra = ((d_true > radius) & (d_rep <= radius)).sum(1) / np.maximum(c_true, 1)
    d2_true = np.hypot(pts[None, :, 0] - stores2[:, None, 0], pts[None, :, 1] - stores2[:, None, 1])
    d2_rep = np.hypot(rp[None, :, 0] - stores2[:, None, 0], rp[None, :, 1] - stores2[:, None, 1])
    swap = ((d_true < d2_true) != (d_rep < d2_rep)).mean(1)
    near = d_true <= radius
    abs_err = np.abs(d_rep - d_true)
    return {"stores": stores, "c_true": c_true, "c_rep": c_rep, "ratio": ratio, "miss": miss, "extra": extra,
            "swap": swap, "abs_err_all": abs_err.mean(), "abs_err_near": abs_err[near].mean(),
            "rel_err_near": (abs_err[near] / np.maximum(d_true[near], 1)).mean(),
            "abs_ratio_over10": (np.abs(ratio) > 0.10).mean()}


def q(a, p):
    return round(float(np.quantile(a, p)), 4)


def run(seed, n_cust=3000, n_chome=48, radius=500.0, dense_share=0.6, dense_sd=250.0, rep="丁目の真ん中"):
    rng = np.random.default_rng(seed)
    ch = make_chome(rng, n_chome)
    pts = make_customers(rng, n_cust, dense_share, dense_sd)
    idx = assign(pts, ch)
    rp = rep_points(pts, idx, ch, rep)
    ev = evaluate(rng, pts, rp, radius)
    pos_err = np.hypot(*(rp - pts).T)
    side = np.sqrt((ch.x1 - ch.x0) * (ch.y1 - ch.y0))
    return ch, pts, idx, rp, ev, pos_err, side


def summary(ev, pos_err):
    return {"pos_err_median_m": round(float(np.median(pos_err)), 1), "pos_err_p90_m": round(float(np.quantile(pos_err, .9)), 1),
            "dist_abs_err_mean_m": round(float(ev["abs_err_all"]), 1),
            "dist_abs_err_near_m": round(float(ev["abs_err_near"]), 1),
            "dist_rel_err_near": round(float(ev["rel_err_near"]), 4),
            "count_ratio_mean": round(float(ev["ratio"].mean()), 4),
            "count_ratio_p10": q(ev["ratio"], .1), "count_ratio_p90": q(ev["ratio"], .9),
            "count_abs_over10_share": round(float(ev["abs_ratio_over10"]), 4),
            "miss_mean": round(float(ev["miss"].mean()), 4), "extra_mean": round(float(ev["extra"].mean()), 4),
            "swap_mean": round(float(ev["swap"].mean()), 4),
            "swap_p10": q(ev["swap"], .1), "swap_p90": q(ev["swap"], .9)}


def main():
    # 1) 基本の町（data に置く）
    ch, pts, idx, rp, ev, pos_err, side = run(SEED, **BASE)
    ch_out = ch.copy()
    ch_out["n_customers"] = np.bincount(idx, minlength=len(ch))
    ch_out["area_m2"] = ((ch.x1 - ch.x0) * (ch.y1 - ch.y0))
    ch_out.round(1).to_csv(DATA / "chome.csv", index=False)
    cust = pd.DataFrame({"customer_id": np.arange(1, len(pts) + 1), "x": pts[:, 0].round(1), "y": pts[:, 1].round(1),
                         "chome": ch.chome.values[idx]})
    cust.to_csv(DATA / "customers.csv", index=False)
    stores = pd.DataFrame({"store_no": np.arange(1, N_STORE + 1), "x": ev["stores"][:, 0].round(1),
                           "y": ev["stores"][:, 1].round(1), "count_true": ev["c_true"], "count_chome": ev["c_rep"],
                           "count_change": ev["ratio"].round(4), "miss_share": ev["miss"].round(4),
                           "extra_share": ev["extra"].round(4), "nearer_store_swap": ev["swap"].round(4)})
    stores.to_csv(RES / "stores_base.csv", index=False)
    base = summary(ev, pos_err)
    # 丁目の大きさの目安：長方形の中で一様なら、真ん中までの距離の平均は一辺の約0.38倍（正方形のとき）
    base["chome_side_median_m"] = round(float(np.median(side)), 1)
    base["chome_side_min_m"] = round(float(side.min()), 1)
    base["chome_side_max_m"] = round(float(side.max()), 1)
    base["chome_customers_min"] = int(ch_out.n_customers.min())
    base["chome_customers_max"] = int(ch_out.n_customers.max())
    base["pos_err_mean_m"] = round(float(pos_err.mean()), 1)
    base["formula_pos_err_mean_m"] = round(float(np.mean(0.3826 * side.values[idx])), 1)
    # 店から近い客ほど、距離の割合のずれは大きい
    d_true = np.hypot(pts[None, :, 0] - ev["stores"][:, None, 0], pts[None, :, 1] - ev["stores"][:, None, 1])
    d_rep = np.hypot(rp[None, :, 0] - ev["stores"][:, None, 0], rp[None, :, 1] - ev["stores"][:, None, 1])
    bands = []
    for lo, hi in [(0, 250), (250, 500), (500, 1000), (1000, 3000)]:
        m = (d_true >= lo) & (d_true < hi)
        e = np.abs(d_rep[m] - d_true[m])
        bands.append({"band_m": f"{lo}〜{hi}", "abs_err_mean_m": round(float(e.mean()), 1),
                      "rel_err_mean": round(float((e / np.maximum(d_true[m], 1)).mean()), 4)})
    pd.DataFrame(bands).to_csv(RES / "distance_bands.csv", index=False)
    # 半径の中の人数の増減と、店の場所で人が集まるところの境目か
    worst_up = stores.sort_values("count_change").iloc[-1]
    worst_dn = stores.sort_values("count_change").iloc[0]

    # 2) 確かめ：置き方を1つずつ変える（各10の町 × 店300か所）
    grid = ([("丁目の数", "n_chome", v) for v in [12, 24, 48, 96, 192]] +
            [("半径（m）", "radius", v) for v in [300.0, 500.0, 800.0]] +
            [("代表点", "rep", v) for v in ["丁目の真ん中", "客の重心"]] +
            [("集まる客の割合", "dense_share", v) for v in [0.0, 0.6, 0.9]] +
            [("集まり方の広さ（m）", "dense_sd", v) for v in [150.0, 250.0, 400.0]])
    rob = []
    for k, (lab, key, val) in enumerate(grid):
        p = dict(BASE); p[key] = val
        rs = []
        for i in range(10):
            _, _, _, _, e, pe, _ = run(SEED * 1000 + k * 100 + i, **p)
            rs.append(summary(e, pe))
        rs = pd.DataFrame(rs)
        rob.append({"factor": lab, "key": key, "value": val, "is_base": val == BASE[key],
                    "pos_err_median_m": round(float(rs.pos_err_median_m.mean()), 1),
                    "dist_rel_err_near": round(float(rs.dist_rel_err_near.mean()), 4),
                    "count_ratio_mean": round(float(rs.count_ratio_mean.mean()), 4),
                    "count_ratio_p10": round(float(rs.count_ratio_p10.mean()), 4),
                    "count_ratio_p90": round(float(rs.count_ratio_p90.mean()), 4),
                    "count_abs_over10_share": round(float(rs.count_abs_over10_share.mean()), 4),
                    "miss_mean": round(float(rs.miss_mean.mean()), 4),
                    "extra_mean": round(float(rs.extra_mean.mean()), 4),
                    "swap_mean": round(float(rs.swap_mean.mean()), 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    rb = rob[rob.key.isin(["n_chome", "radius", "dense_share", "dense_sd"])]
    out = {"settings_base": BASE, "dense_points": DENSE, "town_side_m": L, "n_store_positions": N_STORE,
           "base_town": base, "distance_bands": bands,
           "store_most_up": {"x": float(worst_up.x), "y": float(worst_up.y), "count_true": int(worst_up.count_true),
                             "count_chome": int(worst_up.count_chome), "change": float(worst_up.count_change)},
           "store_most_down": {"x": float(worst_dn.x), "y": float(worst_dn.y), "count_true": int(worst_dn.count_true),
                               "count_chome": int(worst_dn.count_chome), "change": float(worst_dn.count_change)},
           "robustness_over10_range": {"min": float(rb.count_abs_over10_share.min()), "max": float(rb.count_abs_over10_share.max())},
           "robustness_swap_range": {"min": float(rb.swap_mean.min()), "max": float(rb.swap_mean.max())},
           "robustness_p10_p90_widest": {"p10": float(rb.count_ratio_p10.min()), "p90": float(rb.count_ratio_p90.max())}}
    json.dump(out, open(RES / "a951_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：架空の丁目と客、代表点
    fig, ax = plt.subplots(figsize=(6.6, 6.6))
    ax.scatter(pts[:, 0], pts[:, 1], s=2, color=BLUE, alpha=.35, lw=0, label="客の本当の場所")
    for _, r in ch.iterrows():
        ax.add_patch(Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0, fill=False, ec=GRAY, lw=.7))
    for t in TOWNS:
        g = ch[ch.town == t]
        ax.add_patch(Rectangle((g.x0.min(), g.y0.min()), g.x1.max() - g.x0.min(), g.y1.max() - g.y0.min(),
                               fill=False, ec=INK, lw=1.6))
    ax.scatter(ch.cx, ch.cy, s=np.bincount(idx, minlength=len(ch)) / 3, color=ORANGE, alpha=.8,
               ec="white", lw=.5, label="丁目の真ん中（丸の大きさ＝客の数）")
    for _, r in ch.iterrows():
        if (r.x1 - r.x0) > 230 and (r.y1 - r.y0) > 130:
            ax.text(r.x0 + 12, r.y1 - 12, r.chome, fontsize=6, color=INK, va="top")
    ax.set_xlim(0, L); ax.set_ylim(0, L); ax.set_aspect("equal")
    ax.set_xlabel("東西（m）"); ax.set_ylabel("南北（m）")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=False, fontsize=9, markerscale=3)
    ax.set_title(f"架空の町（{len(ch)}丁目・客{len(pts):,}人）。太線は町、細線は丁目（名前は幅の広い丁目だけ）", fontsize=11.5)
    save(fig, "a951_chome_map.png", SRC, y=-0.005)

    # 図2：店の場所ごとの、半径500mの人数のずれ
    fig, ax = plt.subplots(figsize=(7.4, 5.9))
    for _, r in ch.iterrows():
        ax.add_patch(Rectangle((r.x0, r.y0), r.x1 - r.x0, r.y1 - r.y0, fill=False, ec=LIGHT, lw=.7))
    v = stores.count_change.values * 100
    lim = max(5, np.ceil(np.abs(v).max() / 5) * 5)
    sc = ax.scatter(stores.x, stores.y, c=v, cmap="RdBu_r", vmin=-lim, vmax=lim, s=26, ec=GRAY, lw=.3)
    cb = fig.colorbar(sc, ax=ax, shrink=.85, pad=.03)
    cb.set_label("丁目の真ん中で数えた人数のずれ（%）")
    for (dx, dy) in DENSE:
        ax.add_patch(Circle((dx, dy), BASE["dense_sd"], fill=False, ec=INK, ls="--", lw=.9))
    ax.set_xlim(0, L); ax.set_ylim(0, L); ax.set_aspect("equal")
    ax.set_xlabel("店を置いた場所の東西（m）。点線の円は客が集まるところ"); ax.set_ylabel("南北（m）")
    ax.set_title(f"半径{int(BASE['radius'])}mの客の数：店の{N_STORE}か所のうち{base['count_abs_over10_share'] * 100:.0f}%で±10%を超えてずれた",
                 fontsize=11)
    save(fig, "a951_store_shift.png", SRC)

    # 図3：確かめ（丁目の数を変えると）
    g = rob[rob.key == "n_chome"]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    x = g.value.astype(int).astype(str)
    axes[0].bar(x, g.count_abs_over10_share * 100, color=[ORANGE if b else LIGHT for b in g.is_base])
    for xx, yy in zip(x, g.count_abs_over10_share * 100):
        axes[0].text(xx, yy + 1, f"{yy:.0f}%", ha="center", fontsize=9)
    axes[0].set_ylabel("人数が±10%を超えてずれた\n店の場所の割合（%）", linespacing=1.6)
    axes[0].set_xlabel("丁目の数（町全体）")
    axes[0].set_ylim(0, 100)
    axes[1].bar(x, g.swap_mean * 100, color=[ORANGE if b else LIGHT for b in g.is_base])
    for xx, yy in zip(x, g.swap_mean * 100):
        axes[1].text(xx, yy + .1, f"{yy:.1f}%", ha="center", fontsize=9)
    axes[1].set_ylabel("2店のどちらが近いかが\n入れ替わった客の割合（%）", linespacing=1.6)
    axes[1].set_xlabel("丁目の数（町全体）")
    fig.suptitle(f"丁目が大きい（数が少ない）ほど、ずれは大きい（半径{int(BASE['radius'])}m、各10の町×店{N_STORE}か所）",
                 fontsize=11.5)
    fig.tight_layout()
    save(fig, "a951_robustness.png", SRC)


if __name__ == "__main__":
    main()
