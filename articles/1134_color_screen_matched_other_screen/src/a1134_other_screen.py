"""1134 1台の画面で合わせた色は、色の出方の違う別の画面でどれだけずれるのか？（架空のデータ）

架空の商品の写真に見立てた色の板24枚（灰色6・淡い色9・あざやかな色9）を、作成者が置いた「正しい見え方」で表す。
画面ごとの色の出方（3色それぞれの明るさの曲がり方・強さ・黒の浮き・3色の色みのずれ）を作成者が乱数で置く。
画面Aで見ながら、正しい見え方になるまで板の色の値を直して保存し（Aで出せない色は出せる端で止まる）、
同じファイルを別の画面Bで見たときの色の差を、直さないファイルをBで見たときと比べる。
色の差は、作成者が置いた見え方の式（明るさ0〜100と2つの色みの軸に直した距離）で数える。
"""
import json
import time
import itertools
import colorsys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1134
SRC = "架空の色の板と架空の画面（作成者が置いた色の出方からの乱数、seed 1134）"
GAMMA = 2.2
# 3色の強さから色（見え方の基準の3つの値）への換算（作成者が置いた正しい見え方）
M0 = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = M0.sum(1)
BASE = {"curve_sd": 0.05, "gain_sd": 0.04, "mix_sd": 0.03, "black_max": 0.01}
REPS = 4000
GRID_REPS = 1500
SCALES = [0.5, 1.0, 2.0]
NEAR = 2.0   # 「ほぼ同じ」と置いた差
SEEN = 5.0   # 「並べると分かる」と置いた差


def r(x, d=2):
    return round(float(x), d)


def make_patches(rng):
    rows = []
    for i, v in enumerate(np.linspace(0.12, 0.92, 6)):
        rows.append(("灰色", v, v, v))
    for kind, slo, shi, n in [("淡い色", 0.2, 0.45, 9), ("あざやかな色", 0.75, 1.0, 9)]:
        hues = (np.arange(n) / n + rng.uniform(0, 1 / n, n)) % 1
        for h in hues:
            s = rng.uniform(slo, shi)
            val = rng.uniform(0.45, 0.92)
            rows.append((kind,) + colorsys.hsv_to_rgb(h, s, val))
    df = pd.DataFrame(rows, columns=["kind", "r", "g", "b"])
    df.insert(0, "patch", np.arange(1, len(df) + 1))
    return df


def to_view(xyz):
    """作成者が置いた見え方の式：明るさ（0〜100）と2つの色みの軸"""
    t = xyz / WHITE
    f = np.where(t > 0.008856, np.cbrt(np.maximum(t, 1e-12)), 7.787 * t + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def make_screens(rng, n, p, scale=1.0):
    """画面 n 台の色の出方。scale は基準の画面からの離れ方の倍率"""
    g_common = rng.normal(0, p["curve_sd"], (n, 1))
    g_ch = rng.normal(0, p["curve_sd"] / 2, (n, 3))
    gamma = GAMMA * np.exp(scale * (g_common + g_ch))
    gain = np.exp(scale * (rng.normal(0, p["gain_sd"], (n, 1)) + rng.normal(0, p["gain_sd"], (n, 3))))
    black = scale * rng.uniform(0, p["black_max"], (n, 1))
    E = scale * rng.normal(0, p["mix_sd"], (n, 3, 3))
    E[:, np.arange(3), np.arange(3)] = 0          # 3色それぞれに、ほかの色が少しまざる
    M = M0[None] @ (np.eye(3)[None] + E)
    return {"gamma": gamma, "gain": gain, "black": black, "M": M}


def take(s, idx):
    return {k: v[idx] for k, v in s.items()}


def show(s, v):
    """画面 s に色の値 v（板×3、0〜1）を出したときの色（基準の3つの値）。s は1台分を板の数だけ並べたもの"""
    lin = s["black"] + (1 - s["black"]) * np.minimum(s["gain"] * np.clip(v, 0, 1) ** s["gamma"], 1.0)
    return np.einsum("nij,nj->ni", s["M"], lin)


def correct_for(s, target_xyz):
    """画面 s で target_xyz に見えるように色の値を直す。出せない所は0〜1の端で止まる"""
    lin = np.einsum("nij,nj->ni", np.linalg.inv(s["M"]), target_xyz)
    x = (lin - s["black"]) / (1 - s["black"]) / s["gain"]
    return np.clip(x, 0, 1) ** (1 / s["gamma"])


def run(rng, patches, p, n_pairs, scale=1.0, scale_a=None):
    v = patches[["r", "g", "b"]].to_numpy()
    k = len(v)
    target = (M0 @ (v ** GAMMA).T).T
    tv = to_view(target)
    A = make_screens(rng, n_pairs, p, scale if scale_a is None else scale_a)
    B = make_screens(rng, n_pairs, p, scale)
    rep = np.repeat(np.arange(n_pairs), k)
    vv = np.tile(v, (n_pairs, 1))
    tt = np.tile(target, (n_pairs, 1))
    tvv = np.tile(tv, (n_pairs, 1))
    a, b = take(A, rep), take(B, rep)
    d_plain_a = np.linalg.norm(to_view(show(a, vv)) - tvv, axis=1).reshape(n_pairs, k)
    d_plain_b = np.linalg.norm(to_view(show(b, vv)) - tvv, axis=1).reshape(n_pairs, k)
    vc = correct_for(a, tt)
    d_corr_a = np.linalg.norm(to_view(show(a, vc)) - tvv, axis=1).reshape(n_pairs, k)
    d_corr_b = np.linalg.norm(to_view(show(b, vc)) - tvv, axis=1).reshape(n_pairs, k)
    return {"plain_a": d_plain_a, "plain_b": d_plain_b, "corr_a": d_corr_a, "corr_b": d_corr_b,
            "vc": vc.reshape(n_pairs, k, 3)}


def summary(res, kinds):
    pb, ca, cb, pa = res["plain_b"], res["corr_a"], res["corr_b"], res["plain_a"]
    out = {"plain_b_mean": r(pb.mean()), "corr_a_mean": r(ca.mean()), "corr_b_mean": r(cb.mean()),
           "plain_a_mean": r(pa.mean()),
           "ratio_corr_b_to_plain_b": r(cb.mean() / pb.mean(), 3),
           "worse_pair_share_pct": r(100 * (cb.mean(1) > pb.mean(1) + 1e-6).mean()),
           "plain_b_seen_pct": r(100 * (pb > SEEN).mean()), "corr_b_seen_pct": r(100 * (cb > SEEN).mean()),
           "corr_a_near_pct": r(100 * (ca <= NEAR).mean()), "plain_b_near_pct": r(100 * (pb <= NEAR).mean()),
           "corr_b_near_pct": r(100 * (cb <= NEAR).mean())}
    by = []
    for kd in ["灰色", "淡い色", "あざやかな色"]:
        m = kinds == kd
        by.append({"kind": kd, "plain_b": r(pb[:, m].mean()), "corr_a": r(ca[:, m].mean()),
                   "corr_b": r(cb[:, m].mean()), "corr_b_seen_pct": r(100 * (cb[:, m] > SEEN).mean())})
    return out, by


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    patches = make_patches(rng)
    kinds = patches["kind"].to_numpy()

    # 基本
    res = run(np.random.default_rng(SEED + 1), patches, BASE, REPS)
    base, by_kind = summary(res, kinds)
    # A と B の差が小さく独立なら、Aで直したファイルをBで見た差は直さないときの約√2倍（式の目安）
    base["sqrt2"] = r(np.sqrt(2), 3)

    # 例の1組（いちばん差の大きくなる組でも小さい組でもない、中ほどの組）
    pair_mean = res["corr_b"].mean(1)
    ex_i = int(np.argsort(pair_mean)[len(pair_mean) // 2])
    ex = patches.copy()
    ex["corrected_r"], ex["corrected_g"], ex["corrected_b"] = res["vc"][ex_i].T
    ex["diff_plain_on_b"] = res["plain_b"][ex_i]
    ex["diff_corr_on_a"] = res["corr_a"][ex_i]
    ex["diff_corr_on_b"] = res["corr_b"][ex_i]
    patches.to_csv(DATA / "patches.csv", index=False, float_format="%.4f")
    ex.to_csv(DATA / "example_pair.csv", index=False, float_format="%.4f")

    # 画面Aが基準の画面にどれだけ近いか（Aの離れ方の倍率）
    near_rows = []
    for sa in [0.0, 0.25, 0.5, 1.0, 1.5, 2.0]:
        rr = run(np.random.default_rng(SEED + 2), patches, BASE, REPS, 1.0, sa)
        s, _ = summary(rr, kinds)
        near_rows.append({"a_scale": sa, "plain_b": s["plain_b_mean"], "corr_a": s["corr_a_mean"],
                          "corr_b": s["corr_b_mean"], "ratio": s["ratio_corr_b_to_plain_b"],
                          "worse_pair_share_pct": s["worse_pair_share_pct"]})
    near = pd.DataFrame(near_rows)
    near.to_csv(RES / "by_a_closeness.csv", index=False)

    # 1組ごと：Aの直さないときの差（Aが基準から離れている大きさ）と、Bで見た差の増え方
    pa_pair = res["plain_a"].mean(1)
    pb_pair = res["plain_b"].mean(1)
    cb_pair = res["corr_b"].mean(1)
    q = np.quantile(pa_pair, [0, 0.25, 0.5, 0.75, 1])
    bins = []
    for i in range(4):
        m = (pa_pair >= q[i]) & (pa_pair <= q[i + 1]) if i == 3 else (pa_pair >= q[i]) & (pa_pair < q[i + 1])
        bins.append({"a_off_quarter": i + 1, "a_plain_mean": r(pa_pair[m].mean()), "plain_b": r(pb_pair[m].mean()),
                     "corr_b": r(cb_pair[m].mean()), "worse_pair_share_pct": r(100 * (cb_pair[m] > pb_pair[m] + 1e-6).mean())})
    pd.DataFrame(bins).to_csv(RES / "by_a_offset_quarter.csv", index=False)

    # 確かめ：置き方を変えた27通り（明るさの曲がり方・強さ・色みのずれ の大きさを 0.5・1・2倍）
    grid = []
    for i, (sg, sw, sp) in enumerate(itertools.product(SCALES, SCALES, SCALES)):
        p = dict(BASE, curve_sd=BASE["curve_sd"] * sg, gain_sd=BASE["gain_sd"] * sw, mix_sd=BASE["mix_sd"] * sp)
        rr = run(np.random.default_rng(SEED * 100 + i), patches, p, GRID_REPS)
        s, bk = summary(rr, kinds)
        grid.append({"curve_x": sg, "gain_x": sw, "mix_x": sp, "plain_b": s["plain_b_mean"], "corr_a": s["corr_a_mean"],
                     "corr_b": s["corr_b_mean"], "ratio": s["ratio_corr_b_to_plain_b"],
                     "worse_pair_share_pct": s["worse_pair_share_pct"], "corr_b_seen_pct": s["corr_b_seen_pct"],
                     "gray_corr_b": bk[0]["corr_b"], "vivid_corr_b": bk[2]["corr_b"]})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    pd.DataFrame(by_kind).to_csv(RES / "by_kind.csv", index=False)

    out = {"settings": {"seed": SEED, "patches": len(patches), "pairs": REPS, "grid_pairs": GRID_REPS, **BASE,
                        "near_threshold": NEAR, "seen_threshold": SEEN},
           "base": base, "by_kind": by_kind, "by_a_closeness": near_rows, "by_a_offset_quarter": bins,
           "example_pair": {"index": ex_i, "plain_b": r(ex["diff_plain_on_b"].mean()),
                            "corr_a": r(ex["diff_corr_on_a"].mean()), "corr_b": r(ex["diff_corr_on_b"].mean())},
           "grid_range": {"ratio_min": r(grid.ratio.min(), 3), "ratio_max": r(grid.ratio.max(), 3),
                          "worse_min": r(grid.worse_pair_share_pct.min()), "worse_max": r(grid.worse_pair_share_pct.max()),
                          "corr_b_min": r(grid.corr_b.min()), "corr_b_max": r(grid.corr_b.max()),
                          "plain_b_min": r(grid.plain_b.min()), "plain_b_max": r(grid.plain_b.max()),
                          "corr_a_min": r(grid.corr_a.min()), "corr_a_max": r(grid.corr_a.max()),
                          "vivid_over_gray_count": int((grid.vivid_corr_b > grid.gray_corr_b).sum())}}
    json.dump(out, open(RES / "a1134_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    figures(patches, ex, res, ex_i, by_kind, near, grid, base)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


def view_rgb(xyz):
    """色（基準の3つの値）を、正しい見え方の色の値に戻して図に塗る"""
    lin = (np.linalg.inv(M0) @ xyz.T).T
    return np.clip(np.clip(lin, 0, 1) ** (1 / GAMMA), 0, 1)


def figures(patches, ex, res, ex_i, by_kind, near, grid, base):
    v = patches[["r", "g", "b"]].to_numpy()
    k = len(v)
    # 図1：例の1組
    rng = np.random.default_rng(SEED + 1)
    A = make_screens(rng, REPS, BASE)
    B = make_screens(rng, REPS, BASE)
    a = take(A, np.full(k, ex_i))
    b = take(B, np.full(k, ex_i))
    vc = ex[["corrected_r", "corrected_g", "corrected_b"]].to_numpy()
    rows = [("正しい見え方", v, None),
            ("直さないファイルを画面Bで", view_rgb(show(b, v)), ex["diff_plain_on_b"].to_numpy()),
            ("画面Aで合わせたファイルを画面Aで", view_rgb(show(a, vc)), ex["diff_corr_on_a"].to_numpy()),
            ("画面Aで合わせたファイルを画面Bで", view_rgb(show(b, vc)), ex["diff_corr_on_b"].to_numpy())]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for ri, (lab, cols, d) in enumerate(rows):
        for j in range(k):
            ax.add_patch(plt.Rectangle((j, -ri - 0.9), 0.9, 0.8, color=cols[j]))
            if d is not None:
                ax.text(j + 0.45, -ri - 0.97, f"{d[j]:.1f}", ha="center", va="top", fontsize=6.5, color=INK)
        txt = lab if d is None else f"{lab}（色の差の平均 {d.mean():.2f}）"
        ax.text(-0.2, -ri - 0.5, txt, ha="right", va="center", fontsize=9)
    ax.set_xlim(-9.5, k + 0.2)
    ax.set_ylim(-4.3, 0.1)
    ax.axis("off")
    ax.set_title("例の1組：画面Aで合わせた色を画面Bで見る（数字は板ごとの色の差）")
    save(fig, "a1134_example.png", SRC)

    # 図2：板の種類ごとの色の差の平均
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    labs = [d["kind"] for d in by_kind]
    x = np.arange(len(labs))
    w = 0.26
    for off, key, col, name in [(-w, "plain_b", GRAY, "直さないファイルを画面Bで"),
                                (0, "corr_a", GREEN, "画面Aで合わせて画面Aで"),
                                (w, "corr_b", ORANGE, "画面Aで合わせて画面Bで")]:
        vals = [d[key] for d in by_kind]
        ax.bar(x + off, vals, w, color=col, label=name)
        for xi, vv in zip(x + off, vals):
            ax.text(xi, vv + 0.05, f"{vv:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, labs)
    ax.set_ylim(0, max(d["corr_b"] for d in by_kind) * 1.25)
    ax.set_ylabel("色の差の平均（作成者が置いた式）")
    ax.set_title(f"画面Bでは、Aで合わせたファイルのほうが平均の差が大きかった（{REPS:,}組）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1134_by_kind.png", SRC)

    # 図3：画面Aの基準からの離れ方と、27通り
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axs[0]
    ax.plot(near.a_scale, near.corr_b, "o-", color=ORANGE, label="画面Aで合わせて画面Bで")
    ax.plot(near.a_scale, near.plain_b, "o--", color=GRAY, label="直さないファイルを画面Bで")
    for xx, yy in zip(near.a_scale, near.corr_b):
        ax.text(xx, yy + 0.35, f"{yy:.2f}", ha="center", fontsize=8, color=ORANGE)
    ax.set_xlabel("画面Aの、基準の画面からの離れ方（Bを1とした倍率）")
    ax.set_ylabel("画面Bでの色の差の平均")
    ax.set_ylim(0, near.corr_b.max() * 1.2)
    ax.set_title("Aが基準から離れているほど、Bでずれる")
    ax.legend(frameon=False, fontsize=8.5)
    ax = axs[1]
    ax.scatter(grid.plain_b, grid.corr_b, color=BLUE, s=22)
    mx = grid.corr_b.max() * 1.1
    xs = np.linspace(0, mx, 10)
    ax.plot(xs, xs, color=GRAY, lw=1)
    ax.plot(xs, xs * np.sqrt(2), color=GRAY, lw=1, ls="--")
    ax.text(mx * 0.62, mx * 0.55, "同じ", color=GRAY, fontsize=8.5)
    ax.text(mx * 0.25, mx * 0.25 * 1.414 + 0.6, "√2倍", color=GRAY, fontsize=8.5, ha="right")
    ax.set_xlim(0, mx / 1.0)
    ax.set_ylim(0, mx)
    ax.set_xlabel("直さないファイルを画面Bで（色の差の平均）")
    ax.set_ylabel("画面Aで合わせて画面Bで")
    ax.set_title(f"置き方27通り：直さないときの{grid.ratio.min():.3f}〜{grid.ratio.max():.3f}倍", fontsize=11.5)
    save(fig, "a1134_robust.png", SRC)


if __name__ == "__main__":
    main()
