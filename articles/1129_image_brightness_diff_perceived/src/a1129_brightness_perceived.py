"""1129 明るさの差を数値のまま測ると、人が見て感じる差とどこでずれるのか？（架空のデータ）

画素の値 v（0〜255）と、作成者が置いた「見え方の式」で数えた明るさの感じ方 L（0〜100）の差を比べる。
  光の強さ Y = (v/255)^g（光の強さの指数 g = 2.2）
  感じる明るさ L = 100 ×（1.16 × Y^(1/3) − 0.16）。ごく暗い所（Y < 0.008856）は 0 からまっすぐ結ぶ（つなぎ目で値と傾きがそろう）
  差に気づける：|ΔL| ≥ 1（作成者が置いた境目）
色のついた板では Y = 0.2126×R + 0.7152×G + 0.0722×B（R, G, B はそれぞれ光の強さに直した値）。
これは作成者が置いた式で、人に見せて確かめたものではない。
架空の商品の写真に見立てた「色の板」の組 20,000組（明るさ0〜255、2枚の差 −12〜12）で、
画素の値の差で並べたときと、置いた式の差で並べたときに、どこでずれるかを数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1129
SRC = "架空の色の板と作成者が置いた見え方の式（作成者が式と乱数で作成、seed 1129）"
BASE = {"gamma": 2.2, "p": 1 / 3, "thr": 1.0}
YT = 0.008856
W = np.array([0.2126, 0.7152, 0.0722])
N_PAIRS = 20000
MAXD = 12
GRID_GAMMA = [1.8, 2.2, 2.6]
GRID_P = [0.25, 1 / 3, 0.5]
GRID_THR = [0.5, 1.0, 2.0]


def r(x, d=2):
    return round(float(x), d)


def light(v, gamma):
    return (np.asarray(v, float) / 255) ** gamma


def feel(Y, p):
    """L = 100×((1+a)×Y^p − a)。ごく暗い所は 0 からの直線で、つなぎ目で値も傾きもそろうように a を決める"""
    Y = np.asarray(Y, float)
    a = (1 - p) * YT ** p / (1 - (1 - p) * YT ** p)
    slope = 100 * (1 + a) * p * YT ** (p - 1)
    return np.where(Y >= YT, 100 * ((1 + a) * np.maximum(Y, YT) ** p - a), slope * Y)


def L_gray(v, gamma, p):
    return feel(light(v, gamma), p)


def L_rgb(rgb, gamma, p):
    return feel(light(rgb, gamma) @ W, p)


def min_visible_step(v0, gamma, p, thr):
    """明るさ v0 の板から、上に何段（画素の値）上げると |ΔL| ≥ thr になるか"""
    v = np.arange(256)
    L = L_gray(v, gamma, p)
    out = []
    for a in v0:
        ok = np.where(np.abs(L[a:] - L[a]) >= thr)[0]
        out.append(int(ok[0]) if len(ok) else None)
    return out


def make_pairs(rng, n):
    v1 = rng.integers(0, 256, n)
    d = rng.integers(-MAXD, MAXD + 1, n)
    v2 = np.clip(v1 + d, 0, 255)
    return v1, v2


def rank_corr(a, b):
    ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def pair_stats(v1, v2, gamma, p, thr, rng):
    dv = np.abs(v2 - v1).astype(float)
    dL = np.abs(L_gray(v2, gamma, p) - L_gray(v1, gamma, p))
    dY = np.abs(light(v2, gamma) - light(v1, gamma)) * 100
    mid = (v1 + v2) / 2
    vis = dL >= thr
    share_vis = vis.mean()
    # 画素の差の境目 k を「気づける割合」が同じになるように選ぶ
    ks = np.arange(0, MAXD + 2)
    k = int(ks[np.argmin([abs((dv >= kk).mean() - share_vis) for kk in ks])])
    flag = dv >= k
    miss = vis & ~flag      # 置いた式では気づけるのに、画素の差では小さいとした
    false = ~vis & flag     # 置いた式では気づけないのに、画素の差では大きいとした
    dark, bright = mid < 64, mid >= 192
    # 光の強さの差でも、同じように境目を合わせて分ける
    qy = np.quantile(dY, 1 - share_vis)
    flag_y = dY >= qy
    wrong_y = (vis != flag_y)
    # 組どうしで「どちらの差が大きいか」が入れかわる割合（同じ値の組は除く）
    i = rng.integers(0, len(dv), 200000); j = rng.integers(0, len(dv), 200000)
    a = np.sign(dv[i] - dv[j]); b = np.sign(dL[i] - dL[j])
    m = (a != 0) & (b != 0)
    return {
        "share_visible": r(share_vis * 100, 2), "pixel_cut": k, "share_flag": r(flag.mean() * 100, 2),
        "share_wrong": r((miss | false).mean() * 100, 2),
        "share_miss": r(miss.mean() * 100, 2), "share_false": r(false.mean() * 100, 2),
        "wrong_in_dark": r(dark[miss | false].mean() * 100, 1),
        "wrong_in_bright": r(bright[miss | false].mean() * 100, 1),
        "wrong_below_16": r((mid[miss | false] < 16).mean() * 100, 1),
        "share_dark": r(dark.mean() * 100, 1), "share_bright": r(bright.mean() * 100, 1),
        "rank_corr_pixel_feel": r(rank_corr(dv, dL), 3), "rank_corr_light_feel": r(rank_corr(dY, dL), 3),
        "rank_corr_pixel_light": r(rank_corr(dv, dY), 3),
        "share_order_flip": r((a[m] != b[m]).mean() * 100, 2),
        "light_cut_x100": r(qy, 3), "share_wrong_light": r(wrong_y.mean() * 100, 2),
        "light_miss": r((vis & ~flag_y).mean() * 100, 2), "light_false": r((~vis & flag_y).mean() * 100, 2),
        "light_miss_in_dark": r(dark[vis & ~flag_y].mean() * 100, 1),
        "light_false_in_bright": r(bright[~vis & flag_y].mean() * 100, 1),
    }, dv, dL, mid


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    g, p, thr = BASE["gamma"], BASE["p"], BASE["thr"]

    # ---------- 明るさごと：画素の値で10上げたときの差 ----------
    levels = list(range(0, 246, 5))
    rows = []
    vis_step = min_visible_step(levels, g, p, thr)
    for v0, ms in zip(levels, vis_step):
        rows.append({"v": v0, "dL_up10": r(L_gray(v0 + 10, g, p) - L_gray(v0, g, p), 3),
                     "dY100_up10": r((light(v0 + 10, g) - light(v0, g)) * 100, 3),
                     "L": r(L_gray(v0, g, p), 2), "min_step_visible": ms})
    lev = pd.DataFrame(rows)
    lev.to_csv(RES / "by_level.csv", index=False)
    pick = [10, 30, 60, 120, 180, 240]
    by_pick = {str(v): lev.set_index("v").loc[v].to_dict() for v in pick}
    dl = lev.set_index("v")["dL_up10"]
    dy = lev.set_index("v")["dY100_up10"]

    # ---------- 色の板：灰色128から1色だけ40上げる ----------
    color = {}
    base_rgb = np.array([128, 128, 128])
    for name, ch in [("赤", 0), ("緑", 1), ("青", 2)]:
        c = base_rgb.copy(); c[ch] += 40
        color[name] = r(L_rgb(c, g, p) - L_rgb(base_rgb, g, p), 3)
    color["緑÷青"] = r(color["緑"] / color["青"], 2)
    # 色の板の組：画素の値の距離（3色の差の二乗和の平方根）と明るさの感じ方の差
    n = N_PAIRS
    c1 = rng.integers(0, 256, (n, 3))
    c2 = np.clip(c1 + rng.integers(-MAXD, MAXD + 1, (n, 3)), 0, 255)
    dist = np.sqrt(((c1 - c2) ** 2).sum(1))
    dLc = np.abs(L_rgb(c2, g, p) - L_rgb(c1, g, p))
    near = (dist >= 10) & (dist <= 12)
    color_pairs = {
        "rank_corr_rgbdist_feel": r(rank_corr(dist, dLc), 3),
        "n_dist_10_12": int(near.sum()),
        "dL_at_dist_10_12_p10_p90": [r(np.percentile(dLc[near], 10)), r(np.percentile(dLc[near], 90))],
        "share_invisible_at_dist_10_12": r((dLc[near] < thr).mean() * 100, 1),
    }
    pd.DataFrame({"r1": c1[:, 0], "g1": c1[:, 1], "b1": c1[:, 2], "r2": c2[:, 0], "g2": c2[:, 1], "b2": c2[:, 2],
                  "rgb_dist": dist.round(3), "dL": dLc.round(4)}).to_csv(DATA / "color_pairs.csv", index=False)

    # ---------- 灰色の板の組 ----------
    v1, v2 = make_pairs(rng, N_PAIRS)
    st, dv, dL, mid = pair_stats(v1, v2, g, p, thr, rng)
    pd.DataFrame({"v1": v1, "v2": v2, "pixel_diff": dv.astype(int), "dL": dL.round(4)}).to_csv(
        DATA / "gray_pairs.csv", index=False)

    # ---------- 確かめ：27通り ----------
    grid = []
    for gg, pp, tt in itertools.product(GRID_GAMMA, GRID_P, GRID_THR):
        s2, *_ = pair_stats(v1, v2, gg, pp, tt, np.random.default_rng(SEED + 1))
        ms = min_visible_step([20, 120, 235], gg, pp, tt)
        d20 = float(L_gray(30, gg, pp) - L_gray(20, gg, pp)); d235 = float(L_gray(245, gg, pp) - L_gray(235, gg, pp))
        grid.append({"gamma": gg, "p": r(pp, 4), "thr": tt, "dL_up10_at20": r(d20, 3), "dL_up10_at235": r(d235, 3),
                     "ratio_20_vs_235": r(d20 / d235, 2), "min_step_at20": ms[0], "min_step_at120": ms[1],
                     "min_step_at235": ms[2], **s2})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsum = {c: [r(grid[c].min(), 3), r(grid[c].max(), 3)] for c in
            ["ratio_20_vs_235", "min_step_at20", "min_step_at120", "min_step_at235", "share_wrong", "wrong_in_dark",
             "wrong_in_bright", "light_miss_in_dark", "rank_corr_pixel_feel", "rank_corr_light_feel", "share_order_flip", "pixel_cut",
             "share_wrong_light", "share_visible"]}
    gsum["n_ratio_gt1"] = int((grid.ratio_20_vs_235 > 1).sum())
    gsum["n_pixel_wrong_lt_light_wrong"] = int((grid.share_wrong < grid.share_wrong_light).sum())
    gsum["n"] = int(len(grid))

    res = {
        "base": {"gamma": g, "p": "1/3", "thr": thr, "Y_toe": YT, "weights_rgb": W.tolist()},
        "n_pairs": N_PAIRS, "max_diff": MAXD,
        "by_level_pick": by_pick,
        "dL_up10_max": {"v": int(dl.idxmax()), "dL": r(dl.max(), 3)},
        "dL_up10_min": {"v": int(dl.idxmin()), "dL": r(dl.min(), 3)},
        "dY100_up10_at10": r(dy.loc[10], 3), "dY100_up10_at240": r(dy.loc[240], 3),
        "ratio_dL_max_vs_min": r(dl.max() / dl.min(), 2),
        "ratio_dL_30_vs_240": r(dl.loc[30] / dl.loc[240], 2),
        "ratio_dY_240_vs_10": r(dy.loc[240] / dy.loc[10], 2),
        "color_plus40_from_gray128": color,
        "color_pairs": color_pairs,
        "gray_pairs": st,
        "grid": {"gamma": GRID_GAMMA, "p": [r(x, 4) for x in GRID_P], "thr": GRID_THR, "summary": gsum},
    }

    # ---------- 図1：明るさごとに、画素の値で10上げたときの差 ----------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    ax = axes[0]
    ax.plot(lev.v, lev.dL_up10, "-", color=BLUE, lw=2, label="置いた見え方の式の差")
    ax.plot(lev.v, lev.dY100_up10, "-", color=ORANGE, lw=2, label="光の強さの差（×100）")
    ax.axhline(thr, color=GRAY, ls="--", lw=1, label=f"気づける境目（{thr:g}）")
    ax.set_ylim(0, None); ax.set_xlabel("もとの板の画素の値（0＝黒、255＝白）")
    ax.set_ylabel("画素の値を10上げたときの差"); ax.set_title(f"同じ「10」でも、式の差は{dl.min():.2f}〜{dl.max():.2f}と変わる")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
    ax = axes[1]
    ax.bar(lev.v, lev.min_step_visible, width=4, color=BLUE)
    ax.set_ylim(0, None); ax.set_xlabel("もとの板の画素の値")
    ax.set_ylabel("気づける境目に届く画素の値の差（段）")
    ax.set_title("境目に届く差は、ごく暗い所で大きく、少し暗い所で小さい", fontsize=12)
    ax.grid(alpha=0.3, axis="y")
    fig.suptitle("作成者が置いた見え方の式（光の強さ＝(値/255)^2.2、感じ方＝100×(1.16×強さ^(1/3)−0.16)）での値", fontsize=11, y=1.02)
    fig.tight_layout()
    save(fig, "a1129_by_level.png", SRC)

    # ---------- 図2：灰色の板の組 ----------
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    sel = np.random.default_rng(SEED + 2).choice(len(dv), 3000, replace=False)
    for lab, msk, col in [("暗い組（平均が64未満）", mid < 64, INK), ("中くらい", (mid >= 64) & (mid < 192), GRAY),
                          ("明るい組（192以上）", mid >= 192, ORANGE)]:
        s = sel[msk[sel]]
        jit = np.random.default_rng(SEED + 3).uniform(-0.3, 0.3, len(s))
        ax.scatter(dv[s] + jit, dL[s], s=6, color=col, alpha=0.5, label=lab)
    ax.axhline(thr, color=BLUE, ls="--", lw=1, label=f"置いた式で気づける境目（{thr:g}）")
    ax.axvline(st["pixel_cut"] - 0.5, color=GREEN, ls=":", lw=1.5,
               label=f"画素の差の境目（{st['pixel_cut']}以上を「差あり」）")
    ax.set_xlim(0, MAXD + 1); ax.set_ylim(0, None)
    ax.set_xlabel("2枚の板の画素の値の差"); ax.set_ylabel("置いた見え方の式の差")
    ax.set_title(f"灰色の板の組（3,000組を表示）：2つの境目で分け方が違う組は{st['share_wrong']}%")
    ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=0.3)
    fig.tight_layout()
    save(fig, "a1129_pairs.png", SRC)

    # ---------- 図3：27通り ----------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    lab = [f"光{a}・感じ方{b:.2f}" for a, b in itertools.product(GRID_GAMMA, GRID_P)]
    sub = grid[grid.thr == 1.0].reset_index(drop=True)
    x = np.arange(len(sub))
    axes[0].bar(x - 0.2, sub.min_step_at20, 0.4, color=INK, label="画素の値20から")
    axes[0].bar(x + 0.2, sub.min_step_at235, 0.4, color=ORANGE, label="画素の値235から")
    axes[0].set_xticks(x); axes[0].set_xticklabels(lab, rotation=60, fontsize=8)
    axes[0].set_ylim(0, None); axes[0].set_ylabel("境目（1）に届く画素の値の差（段）")
    axes[0].set_title("境目1のとき：気づける差に要る段（9通り）"); axes[0].legend(fontsize=9)
    axes[1].bar(np.arange(len(grid)), grid.share_wrong, color=BLUE)
    axes[1].set_ylim(0, None); axes[1].set_xlabel("置き方27通り（光の強さの指数×感じ方の指数×境目）")
    axes[1].set_ylabel("分け方が違う組の割合（%）")
    axes[1].set_title(f"画素の差で分けると外れる組：{gsum['share_wrong'][0]}〜{gsum['share_wrong'][1]}%")
    axes[1].set_xticks([])
    for ax in axes:
        ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    save(fig, "a1129_robust.png", SRC)

    with open(RES / "a1129_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
